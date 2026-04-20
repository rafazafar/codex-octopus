## ADDED Requirements

### Requirement: Global system health incident bar
The app SHALL render a persistent global incident bar on all protected pages when the backend reports a warning or critical system-health alert. The bar MUST appear below the main header, show only the highest-severity active alert, and provide a link to the most relevant investigation page.

#### Scenario: Critical system-health alert is shown across protected pages
- **WHEN** `GET /api/system-health` returns `status: "critical"` with an alert payload
- **THEN** the app renders a persistent critical incident bar below the main header on protected routes
- **AND** the bar shows the alert title, message, and investigation link

#### Scenario: Healthy state hides the global incident bar
- **WHEN** `GET /api/system-health` returns `status: "healthy"` with `alert: null`
- **THEN** the app does not render the global incident bar
