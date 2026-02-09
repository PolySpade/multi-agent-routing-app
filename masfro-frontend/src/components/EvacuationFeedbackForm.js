'use client';

import { useState, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

const FEEDBACK_CATEGORIES = [
  { value: 'center_condition', label: 'Center Condition', desc: 'Report issues at a center' },
  { value: 'route_blocked', label: 'Route Blocked', desc: 'Evacuation route is impassable' },
  { value: 'need_supplies', label: 'Need Supplies', desc: 'Request for food, water, medicine' },
  { value: 'all_clear', label: 'All Clear', desc: 'Situation has improved' },
];

export default function EvacuationFeedbackForm({ onClose, prefilledCenter }) {
  const [category, setCategory] = useState('center_condition');
  const [centerName, setCenterName] = useState(prefilledCenter || '');
  const [severity, setSeverity] = useState(0.5);
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState(null);
  const [locationText, setLocationText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  const handleGetLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setMessage('Geolocation not supported.');
      return;
    }
    setMessage('Getting location...');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setLocation(coords);
        setLocationText(`${coords.lat.toFixed(5)}, ${coords.lng.toFixed(5)}`);
        setMessage('Location set.');
      },
      () => setMessage('Could not get location.'),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage('');

    try {
      const res = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          route_id: 'evacuation-feedback',
          feedback_type: category,
          location: location ? [location.lat, location.lng] : null,
          severity: parseFloat(severity),
          description: [
            centerName ? `Center: ${centerName}` : null,
            description.trim() || null,
          ].filter(Boolean).join(' | ') || null,
        }),
      });

      if (res.ok) {
        setMessage('Feedback submitted successfully.');
        setTimeout(() => { if (onClose) onClose(); }, 2000);
      } else {
        const err = await res.json();
        setMessage(`Error: ${err.detail || 'Submission failed'}`);
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{
      background: 'linear-gradient(160deg, rgba(88, 80, 180, 0.95) 0%, rgba(55, 48, 130, 0.95) 50%, rgba(30, 25, 80, 0.98) 100%)',
      borderRadius: '18px',
      padding: '2rem',
      color: 'white',
      maxWidth: '500px',
      width: '100%',
      boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
      border: '1px solid rgba(139, 92, 246, 0.35)',
      maxHeight: '90vh',
      overflowY: 'auto',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>Evacuation Feedback</h2>
          <div style={{ fontSize: '0.8rem', opacity: 0.8, marginTop: '0.25rem' }}>
            Report center or route issues
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.2)',
            color: 'white', borderRadius: '50%', width: '32px', height: '32px',
            cursor: 'pointer', fontSize: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            x
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Category */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
            Category
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            {FEEDBACK_CATEGORIES.map((c) => (
              <button
                key={c.value}
                type="button"
                onClick={() => setCategory(c.value)}
                style={{
                  padding: '0.6rem',
                  borderRadius: '8px',
                  border: category === c.value ? '2px solid rgba(139, 92, 246, 0.8)' : '1px solid rgba(255,255,255,0.15)',
                  background: category === c.value ? 'rgba(139, 92, 246, 0.25)' : 'rgba(0,0,0,0.2)',
                  color: category === c.value ? '#c4b5fd' : 'rgba(255,255,255,0.7)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.8rem',
                  fontWeight: category === c.value ? 700 : 400,
                  transition: 'all 0.2s',
                }}
              >
                <div>{c.label}</div>
                <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '0.15rem' }}>{c.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Center Name */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
            Evacuation Center (optional)
          </label>
          <input
            type="text"
            value={centerName}
            onChange={(e) => setCenterName(e.target.value)}
            placeholder="Name of the evacuation center"
            style={{
              width: '100%', padding: '0.75rem', borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(0,0,0,0.2)',
              color: 'white', fontSize: '0.9rem',
            }}
          />
        </div>

        {/* Severity */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
            Severity: {(severity * 100).toFixed(0)}%
          </label>
          <input
            type="range" min="0" max="1" step="0.1"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            style={{ width: '100%', height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.3)', cursor: 'pointer' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', opacity: 0.7, marginTop: '0.25rem' }}>
            <span>Low</span><span>High</span>
          </div>
        </div>

        {/* Location */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
            Location
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={locationText}
              onChange={(e) => {
                setLocationText(e.target.value);
                const parts = e.target.value.split(',').map((s) => parseFloat(s.trim()));
                if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                  setLocation({ lat: parts[0], lng: parts[1] });
                }
              }}
              placeholder="lat, lng"
              style={{
                flex: 1, padding: '0.75rem', borderRadius: '10px',
                border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(0,0,0,0.2)',
                color: 'white', fontSize: '0.9rem',
              }}
            />
            <button type="button" onClick={handleGetLocation} style={{
              padding: '0.75rem 1rem', borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(0,0,0,0.2)',
              color: 'white', cursor: 'pointer', fontSize: '0.85rem', whiteSpace: 'nowrap',
            }}>
              Use GPS
            </button>
          </div>
        </div>

        {/* Description */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Provide details about the issue..."
            rows={3}
            style={{
              width: '100%', padding: '0.75rem', borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(0,0,0,0.2)',
              color: 'white', fontSize: '0.9rem', resize: 'vertical', fontFamily: 'inherit',
            }}
          />
        </div>

        {/* Status Message */}
        {message && (
          <div style={{
            padding: '0.75rem', borderRadius: '10px',
            background: message.includes('Error') ? 'rgba(239, 68, 68, 0.25)' : 'rgba(34, 197, 94, 0.25)',
            border: `1px solid ${message.includes('Error') ? 'rgba(239,68,68,0.5)' : 'rgba(34,197,94,0.5)'}`,
            fontSize: '0.9rem', textAlign: 'center',
          }}>
            {message}
          </div>
        )}

        {/* Submit */}
        <button type="submit" disabled={isSubmitting} style={{
          padding: '0.95rem', borderRadius: '12px', border: 'none',
          background: isSubmitting ? 'rgba(148,163,184,0.5)' : 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
          color: 'white', fontSize: '1rem', fontWeight: 700,
          cursor: isSubmitting ? 'not-allowed' : 'pointer',
          boxShadow: isSubmitting ? 'none' : '0 12px 28px rgba(139,92,246,0.35)',
          transition: 'all 0.3s',
        }}>
          {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
        </button>
      </form>
    </div>
  );
}
