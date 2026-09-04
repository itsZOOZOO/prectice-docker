-- Go 4 performance indexes (safe to re-run)
CREATE INDEX IF NOT EXISTS ix_clients_clinic_visible_updated
  ON clients (clinic_id, visible, updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_clients_clinic_checkin
  ON clients (clinic_id, check_in_status)
  WHERE visible = true;

CREATE INDEX IF NOT EXISTS ix_clients_clinic_name
  ON clients (clinic_id, name);

CREATE INDEX IF NOT EXISTS ix_notes_clinic_client_created
  ON notes (clinic_id, client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_appointments_clinic_date_time
  ON appointments (clinic_id, appointment_date, appointment_time);

CREATE INDEX IF NOT EXISTS ix_appointments_clinic_doctor_date
  ON appointments (clinic_id, doctor_id, appointment_date);

CREATE INDEX IF NOT EXISTS ix_bills_clinic_client_issued
  ON bills (clinic_id, client_id, issued_at DESC);

CREATE INDEX IF NOT EXISTS ix_receipts_clinic_received
  ON money_receipts (clinic_id, received_at DESC);

CREATE INDEX IF NOT EXISTS ix_receipts_clinic_client
  ON money_receipts (clinic_id, client_id, received_at DESC);

CREATE INDEX IF NOT EXISTS ix_prescriptions_clinic_client_date
  ON prescriptions (clinic_id, client_id, prescription_date DESC);

CREATE INDEX IF NOT EXISTS ix_tasks_clinic_status_created
  ON tasks (clinic_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_tasks_clinic_client
  ON tasks (clinic_id, client_id);
