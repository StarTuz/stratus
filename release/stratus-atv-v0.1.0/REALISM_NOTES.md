# Realism Notes

## GUI Design Philosophy

The Stratus GUI is intended to be a professional-grade interface. Non-realistic elements (such as explicit state history tracking or "magic" flight phase predictors) have been removed from the main interface to maintain immersion.

### Removed Features (Training Aids)

- **VFR Status Panel**: This was used during early development to debug state transitions. In a professional setting, the pilot should infer state from telemetry and ATC instructions.
- **State History Tracking**: Removed to simplify the application state and adhere to the "no magic" rule.

## Radio Frequency Logic

Transmissions are only processed if the radio is tuned to a monitored frequency.

- **Unmonitored**: Total silence.
- **Monitored/Incorrect**: Redirection message provided.
- **Monitored/Correct**: Normal ATC interaction.
