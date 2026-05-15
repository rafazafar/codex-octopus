## ADDED Requirements

### Requirement: Audio transcription excludes Kiro accounts
The system MUST treat audio transcription endpoints as OpenAI-only. Kiro accounts MUST NOT be selected for `/v1/audio/transcriptions` or `/backend-api/transcribe`.

#### Scenario: OpenAI account handles transcription when mixed pool exists
- **WHEN** both OpenAI and Kiro accounts are active
- **AND** a transcription request is received
- **THEN** account selection considers only OpenAI-compatible accounts

#### Scenario: No OpenAI account available for transcription
- **WHEN** only Kiro accounts are eligible
- **AND** a transcription request is received
- **THEN** the system returns a stable OpenAI-compatible no-compatible-account error
- **AND** no Kiro upstream call is made
