## ADDED Requirements

### Requirement: Accounts import accepts current and portable formats

The dashboard accounts import endpoint MUST accept both the existing single-account `auth.json` object format and the external array-based portable account format through the same `POST /api/accounts/import` route.

#### Scenario: Current auth.json payload imports successfully

- **WHEN** the dashboard uploads a valid single-account `auth.json` payload
- **THEN** the system imports one account using the existing account identity and token rules
- **AND** the response reports `format = "auth_json"` and `importedCount = 1`

#### Scenario: External array payload imports successfully

- **WHEN** the dashboard uploads a valid portable array payload containing multiple account records
- **THEN** the system imports every account in the payload through the same route
- **AND** the response reports `format = "portable_json"` and the matching imported count

#### Scenario: Unsupported top-level JSON shape is rejected

- **WHEN** the uploaded file is valid JSON but is neither a supported auth object nor a supported portable array
- **THEN** the system returns a handled `invalid_auth_json` dashboard error
- **AND** no accounts are imported

### Requirement: Bulk account imports are all-or-nothing

Portable batch imports MUST validate and persist as one atomic batch so invalid or conflicting records do not leave partial writes behind.

#### Scenario: One invalid record aborts the batch

- **WHEN** a portable array contains at least one invalid account record
- **THEN** the import request fails
- **AND** none of the records in the uploaded batch are persisted

#### Scenario: Persistence conflict aborts the batch

- **WHEN** a portable array encounters an account identity conflict that the current settings cannot resolve
- **THEN** the import request fails with the existing conflict error behavior
- **AND** none of the accounts from that batch are persisted

### Requirement: Portable import reuses current conflict settings

Account import conflict handling MUST continue to follow the dashboard `importWithoutOverwrite` setting for both current and portable formats.

#### Scenario: Overwrite-enabled import merges matching account identity

- **WHEN** `importWithoutOverwrite` is disabled and an imported record matches an existing account identity
- **THEN** the system updates the existing account instead of creating a duplicate

#### Scenario: Separate-import mode preserves duplicates

- **WHEN** `importWithoutOverwrite` is enabled and an imported record matches an existing account identity
- **THEN** the system preserves both entries using the current duplicate account ID behavior

### Requirement: Accounts export uses the portable external format

The dashboard MUST expose `GET /api/accounts/export` to export all stored accounts as the external portable JSON array format with reusable token material.

#### Scenario: Export returns all accounts as a portable download

- **WHEN** an authenticated dashboard user requests `GET /api/accounts/export`
- **THEN** the system returns an `application/json` attachment containing one external-format record per stored account
- **AND** each record includes the stored email, plan type, account identity, and token trio

#### Scenario: Export leaves unsupported metadata empty

- **WHEN** the export serializer encounters external-format fields that codex-lb does not persist
- **THEN** the system emits stable defaults or `null` values for those fields
- **AND** it does not invent new stored metadata just to populate the export

### Requirement: Import response summarizes batch results

The dashboard import response MUST summarize the detected format and imported accounts so the UI can report clear batch results without losing single-account compatibility.

#### Scenario: Single import keeps convenience account fields

- **WHEN** exactly one account is imported successfully
- **THEN** the response includes summary fields for the batch
- **AND** it also includes the single imported account's convenience fields used by existing callers

#### Scenario: Multi-account import returns account summaries

- **WHEN** multiple accounts are imported successfully
- **THEN** the response includes the imported count, detected format, and a list of imported account summaries
- **AND** the UI can display the imported count without deriving it from side effects
