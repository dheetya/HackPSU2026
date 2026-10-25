
const int btnAuditPin = 2;
const int btnExtractPin = 3; 
const int btnExportPin = 4;  

// Keep track of previous button states to detect new presses
bool lastAuditState = HIGH;
bool lastExtractState = HIGH;
bool lastExportState = HIGH;

void setup() {
  Serial.begin(9600);
  pinMode(btnAuditPin, INPUT_PULLUP);
  pinMode(btnExtractPin, INPUT_PULLUP);
  pinMode(btnExportPin, INPUT_PULLUP);
}

void loop() {
  // Read current states
  bool currentAuditState = digitalRead(btnAuditPin);
  bool currentExtractState = digitalRead(btnExtractPin);
  bool currentExportState = digitalRead(btnExportPin);

  // Check Button 1: Pressed (transition from HIGH to LOW)
  if (lastAuditState == HIGH && currentAuditState == LOW) {
    Serial.println("ACTION_AUDIT_GAPS");
    delay(200); // Debounce delay
  }
  lastAuditState = currentAuditState;

  // Check Button 2: Pressed
  if (lastExtractState == HIGH && currentExtractState == LOW) {
    Serial.println("ACTION_EXTRACT_MATRIX");
    delay(200);
  }
  lastExtractState = currentExtractState;

  // Check Button 3: Pressed
  if (lastExportState == HIGH && currentExportState == LOW) {
    Serial.println("ACTION_EXPORT_SUMMARY");
    delay(200);
  }
  lastExportState = currentExportState;
}