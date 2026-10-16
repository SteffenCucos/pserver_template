# Secure Password Handling Plan

Plan for replacing plaintext password persistence and comparison with a production-appropriate password hashing boundary.

## Goal

The template must never persist, return, log, or compare plaintext passwords.

Use Argon2id through `argon2-cffi` for password hashing and verification, keep password operations behind an injected service, and ensure user API responses cannot serialize credential material.

## Current problems

The current flow has three separate credential leaks:

```text
POST /users
  -> CreateUserRequest.password
  -> User.password
  -> persisted as plaintext

POST /sessions/login
  -> user.password != credentials.password
  -> direct plaintext comparison

GET /users and GET /users/{id}
  -> return the persistence User model
  -> password is serialized into the response
```

The affected code is currently concentrated in:

```text
server/models/user/user.py
server/service/user_service.py
server/api/v1/routes/users.py
server/api/v1/routes/sessions.py
```

## Target design

```text
API request password
  -> UserService
    -> PasswordService.hash_password(...)
      -> Argon2id encoded hash
        -> User.password_hash
          -> repository

Login password
  -> Session/Auth service
    -> PasswordService.verify_password(...)
      -> Argon2id verification
        -> optional rehash after successful login
```

Credential data and public user data must be separate types:

```text
CreateUserRequest   accepts plaintext password at the API boundary
LoginBody           accepts plaintext password at the API boundary
User                internal persistence/domain model with password_hash
UserResponse        API response model with no password-related field
```

## Step 1: Add the password hashing dependency

Add `argon2-cffi` to `requirements.txt`.

Use the high-level `argon2.PasswordHasher` API, which:

- generates a unique random salt for each password;
- stores algorithm and work-factor metadata in the encoded hash;
- performs verification without manually comparing derived values;
- supports `check_needs_rehash(...)` for future parameter upgrades.

Do not implement Argon2 directly and do not generate or store salts in separate application fields.

Start with the library's maintained Argon2id defaults. Benchmark them in the intended deployment environment before production use and keep construction centralized so parameters can be changed without touching routes or domain services.

## Step 2: Add a password service boundary

Create:

```text
server/auth/password/password_service.py
server/auth/password/dependencies.py
```

Suggested interface:

```python
class PasswordService:
    def hash_password(self, password: str) -> str:
        ...

    def verify_password(self, password_hash: str, password: str) -> bool:
        ...

    def needs_rehash(self, password_hash: str) -> bool:
        ...
```

Responsibilities:

```text
hash plaintext passwords
verify passwords using the library API
translate malformed hashes and verification mismatches into False
identify hashes that should be upgraded
hide argon2-specific exceptions from callers
```

The service must not:

```text
persist users
open repositories
create sessions
log plaintext passwords
return password hashes to routes
```

Provide it through FastAPI dependency injection, following the existing service/DAO dependency pattern. Tests should be able to inject a deterministic fake or a low-cost test configuration without changing production code.

## Step 3: Change the persisted user model

Replace:

```python
password: str
```

with:

```python
password_hash: str
```

The explicit name makes accidental plaintext assignment easier to detect in review.

Do not add plaintext password fields to `User`, even temporarily. Plaintext should exist only in request objects and local call frames while a request is being processed.

## Step 4: Hash passwords during user creation

Inject `PasswordService` into `UserService`.

Update `create_user(...)` so it:

1. validates username/email uniqueness;
2. validates the password policy;
3. hashes the supplied password;
4. constructs `User(password_hash=...)`;
5. persists the user;
6. drops all references to the plaintext value after the request completes.

The request type may retain the external field name `password`; clients should not need to know that the stored field is `password_hash`.

Password policy for the starter template should be explicit and separately testable:

```text
minimum length: configurable, default at least 12 characters
maximum length: configurable and high enough for passphrases
no silent truncation
allow spaces and Unicode
reject empty or whitespace-only values
```

Compromised-password screening, account lockout, and rate limiting are valuable follow-up controls but are not substitutes for secure storage.

## Step 5: Verify passwords through the service

Move credential verification out of the route-level direct comparison.

Preferred flow:

```text
sessions.login route
  -> AuthenticationService.authenticate(user_name, password)
    -> UserDAO.get_by_name(...)
    -> PasswordService.verify_password(...)
    -> SessionService.create_session(...)
```

A dedicated `AuthenticationService` is preferable to placing password verification in the route because it keeps the authentication use case testable and prevents future routes from reimplementing credential checks.

Behavior requirements:

```text
unknown username and bad password return the same 401 response
verification mismatch does not raise a 500
malformed stored hashes fail closed
no plaintext or encoded hash appears in logs or exception messages
session creation only occurs after successful verification
```

## Step 6: Rehash on successful login

After a successful verification:

```python
if password_service.needs_rehash(user.password_hash):
    new_hash = password_service.hash_password(credentials.password)
    user_dao.update_password_hash(user._id, new_hash)
```

This allows Argon2 parameters to be strengthened over time without forcing all users to reset their passwords at once.

Add a narrow DAO method such as:

```python
def update_password_hash(self, user_id: Id | str, password_hash: str) -> User | None:
    ...
```

Do not expose a general route that accepts a precomputed password hash.

## Step 7: Stop serializing credential fields

Never return the persistence `User` model directly from API routes.

Add an API-facing model, for example:

```python
@dataclass
class UserResponse:
    _id: str
    user_name: str
    email: str
    email_verified: bool
```

Map `User -> UserResponse` explicitly in:

```text
POST /users
GET /users
GET /users/{user_id}
DELETE /users/{user_id}
```

Returning a dedicated response model is safer than relying on ad hoc field exclusions because newly added internal fields remain private by default.

Recommended endpoint adjustments:

```text
POST /users            -> UserResponse or created user ID
GET /users             -> list[UserResponse]
GET /users/{user_id}   -> UserResponse
DELETE /users/{user_id}-> 204 No Content or UserResponse
```

Add a regression assertion that neither `password` nor `password_hash` appears anywhere in serialized user responses.

## Step 8: Handle existing plaintext records explicitly

The template repository itself should update fixtures and test databases directly. Downstream applications may already contain plaintext records, so document a migration path.

Preferred migration:

1. deploy or run a one-time migration command with access to the user repository and `PasswordService`;
2. read each record containing the legacy `password` field;
3. hash the plaintext value immediately;
4. write `password_hash`;
5. remove the legacy `password` field;
6. verify that no records retain plaintext;
7. invalidate backups, exports, fixtures, and logs that may contain exposed passwords according to the application's incident-response policy.

Because the repository abstraction currently targets Mongo, Postgres, and SQLite, the migration must be tested for all supported backends. If the generic repository cannot remove a field/column, use an explicit backend migration rather than leaving both fields indefinitely.

Do not ship permanent plaintext fallback logic in the normal login path.

For a downstream application that truly requires a zero-downtime rollout, a temporary compatibility release may:

```text
prefer password_hash when present
verify a legacy plaintext value only when password_hash is absent
replace it with an Argon2id hash immediately after successful login
emit a migration metric without logging credential values
be removed after a fixed deadline
```

That compatibility path should not be enabled in newly scaffolded applications.

## Step 9: Tests

### Password service unit tests

```text
hash differs from plaintext
same password produces different encoded hashes
correct password verifies
incorrect password fails
malformed encoded hash fails closed
needs_rehash delegates correctly
plaintext and hash are never logged
```

### User service tests

```text
create_user persists password_hash, not password
create_user never passes plaintext to UserDAO.create
invalid password policy is rejected
username and email uniqueness behavior is unchanged
```

### Authentication tests

```text
valid credentials create a session
bad password returns 401
unknown user returns the same 401 shape
malformed stored hash returns 401
rehash updates the stored hash only after successful login
failed login never creates a session
```

### API regression tests

```text
POST /users response contains no credential field
GET /users contains no credential field
GET /users/{id} contains no credential field
DELETE /users/{id} contains no credential field
stored password is not equal to submitted password
login still succeeds with the submitted password
```

### Backend migration tests

Run the migration against the Mongo, Postgres, and SQLite repository implementations:

```text
legacy password becomes a valid Argon2id hash
legacy password field is removed
migration is restartable/idempotent
already-hashed users are not rehashed unnecessarily
invalid records are reported without exposing their values
```

## Suggested implementation order

```text
PR 1: add PasswordService, dependency wiring, and unit tests
PR 2: change User.password to User.password_hash and hash on creation
PR 3: add AuthenticationService and replace direct login comparison
PR 4: add UserResponse mapping and credential-leak regression tests
PR 5: add rehash-on-login and the narrow DAO update method
PR 6: add/document plaintext-data migration for all backends
PR 7: update README and generated scaffold documentation
```

If this repository is not yet used with persistent real user data, PRs 2 through 4 can be combined because no compatibility rollout is required.

## Acceptance criteria

```text
no plaintext password is persisted
no route compares passwords directly
Argon2id verification is used through one injected service
encoded password hashes never appear in API responses
encoded password hashes and plaintext passwords never appear in logs
successful login can transparently upgrade outdated hash parameters
bad credentials and malformed hashes fail with the same generic 401 response
all existing API authentication tests continue to pass after being updated
Mongo, Postgres, and SQLite behavior is covered
newly scaffolded applications inherit the secure implementation
```

## Non-goals

This workstream does not implement:

```text
password reset emails or reset tokens
multi-factor authentication
OAuth/OpenID Connect
login throttling or account lockout
breached-password API integration
session expiry or rotation
RBAC changes
```

Those should remain separate plans, but rate limiting and password-reset support should be treated as high-priority follow-up authentication work.

## References

- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- RFC 9106, Argon2 Memory-Hard Function: https://www.rfc-editor.org/rfc/rfc9106.html
- argon2-cffi documentation: https://argon2-cffi.readthedocs.io/en/stable/
