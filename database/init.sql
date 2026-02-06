-- Taskio Pro Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tickets table - main entity
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    predicted_category VARCHAR(50),
    actual_category VARCHAR(50),
    confidence_score FLOAT,
    reasoning TEXT,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feedback logs - tracks human corrections for model improvement
CREATE TABLE IF NOT EXISTS feedback_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    old_label VARCHAR(50),
    new_label VARCHAR(50),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(predicted_category);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_ticket ON feedback_logs(ticket_id);

-- Views for analytics
CREATE OR REPLACE VIEW accuracy_metrics AS
SELECT
    COUNT(*) FILTER (WHERE actual_category IS NOT NULL) as total_reviewed,
    COUNT(*) FILTER (WHERE predicted_category = actual_category) as correct_predictions,
    CASE 
        WHEN COUNT(*) FILTER (WHERE actual_category IS NOT NULL) > 0 
        THEN ROUND(
            COUNT(*) FILTER (WHERE predicted_category = actual_category)::NUMERIC / 
            COUNT(*) FILTER (WHERE actual_category IS NOT NULL) * 100, 2
        )
        ELSE 0
    END as accuracy_percentage
FROM tickets;

CREATE OR REPLACE VIEW category_distribution AS
SELECT
    predicted_category as category,
    COUNT(*) as ticket_count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM tickets WHERE predicted_category IS NOT NULL) * 100, 2) as percentage
FROM tickets
WHERE predicted_category IS NOT NULL
GROUP BY predicted_category
ORDER BY ticket_count DESC;

-- Insert sample data for demo
INSERT INTO tickets (title, description, predicted_category, actual_category, confidence_score, reasoning, status) VALUES
('Phone screen cracked', 'My phone screen is cracked after I dropped it yesterday. The touch still works but there is a big crack across the display.', 'Product Issue', 'Product Issue', 0.94, 'Physical damage to device screen - clear hardware issue', 'corrected'),
('App crashes on startup', 'The main app crashes every time I try to open it. Just shows a white screen then closes. Reinstalled but same problem.', 'Software Issue', 'Software Issue', 0.91, 'Application crash on launch - software bug symptoms', 'corrected'),
('WiFi keeps disconnecting', 'WiFi disconnects every few minutes. Have to manually reconnect each time. Other devices work fine on same network.', 'Network Issue', 'Network Issue', 0.89, 'Intermittent WiFi connectivity - network issue', 'corrected'),
('Battery drains in 2 hours', 'Battery goes from 100% to 20% in just 2 hours with minimal use. Used to last all day.', 'Battery Issue', 'Battery Issue', 0.93, 'Rapid battery drain - power management issue', 'corrected'),
('How do I reset my password', 'I forgot my password and need help resetting it. The reset email is not arriving in my inbox.', 'General Question', 'General Question', 0.88, 'Password reset inquiry - general support question', 'corrected');

COMMIT;
