'use client';

import { useState } from 'react';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

export default function FeedbackForm({ routeId, onClose, currentLocation }) {
  const [feedbackType, setFeedbackType] = useState('flooded');
  const [severity, setSeverity] = useState(0.5);
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState(currentLocation || null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage('');

    try {
      const response = await fetch(`${BACKEND_API_URL}/api/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          route_id: routeId || 'general-feedback',
          feedback_type: feedbackType,
          location: location ? [location.lat, location.lng] : null,
          severity: parseFloat(severity),
          description: description.trim() || null,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage('Thank you! Your feedback has been submitted successfully.');
        setTimeout(() => {
          if (onClose) onClose();
        }, 2000);
      } else {
        const errorData = await response.json();
        setMessage(`Error: ${errorData.detail || 'Failed to submit feedback'}`);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      setMessage('Error: Could not submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGetCurrentLocation = () => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      setMessage('Geolocation is not supported in this browser.');
      return;
    }

    setMessage('Requesting location access...');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setMessage('Current location set.');
      },
      (error) => {
        let errorMsg = 'Unable to get current location.';

        switch(error.code) {
          case error.PERMISSION_DENIED:
            errorMsg = 'Location access denied. Please enable location permissions.';
            break;
          case error.POSITION_UNAVAILABLE:
            errorMsg = 'Location information unavailable.';
            break;
          case error.TIMEOUT:
            errorMsg = 'Location request timed out.';
            break;
          default:
            errorMsg = 'Unable to get current location.';
        }

        console.warn('Geolocation error:', errorMsg);
        setMessage(errorMsg);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 1000 * 60
      }
    );
  };

  return (
    <div style={{
      background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%)',
      borderRadius: '18px',
      padding: '2rem',
      color: 'white',
      maxWidth: '500px',
      width: '100%',
      boxShadow: '0 20px 60px rgba(15, 23, 42, 0.5)',
      border: '1px solid rgba(226, 232, 240, 0.25)'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem'
      }}>
        <h2 style={{
          margin: 0,
          fontSize: '1.75rem',
          fontWeight: 700
        }}>
          Submit Feedback
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'rgba(15, 23, 42, 0.25)',
              border: '1px solid rgba(255,255,255,0.2)',
              color: 'white',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              cursor: 'pointer',
              fontSize: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            ×
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div>
          <label style={{
            display: 'block',
            marginBottom: '0.5rem',
            fontSize: '0.95rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05rem',
            opacity: 0.9
          }}>
            Condition Type
          </label>
          <select
            value={feedbackType}
            onChange={(e) => setFeedbackType(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem',
              borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.3)',
              background: 'rgba(15, 23, 42, 0.25)',
              color: 'white',
              fontSize: '1rem',
              cursor: 'pointer'
            }}
          >
            <option value="flooded" style={{ background: '#1e293b', color: 'white' }}>Flooded</option>
            <option value="blocked" style={{ background: '#1e293b', color: 'white' }}>Road Blocked</option>
            <option value="clear" style={{ background: '#1e293b', color: 'white' }}>Road Clear</option>
            <option value="traffic" style={{ background: '#1e293b', color: 'white' }}>Heavy Traffic</option>
          </select>
        </div>

        <div>
          <label style={{
            display: 'block',
            marginBottom: '0.5rem',
            fontSize: '0.95rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05rem',
            opacity: 0.9
          }}>
            Severity: {(severity * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            style={{
              width: '100%',
              height: '8px',
              borderRadius: '4px',
              background: 'rgba(255, 255, 255, 0.3)',
              outline: 'none',
              cursor: 'pointer'
            }}
          />
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '0.8rem',
            opacity: 0.7,
            marginTop: '0.25rem'
          }}>
            <span>Low</span>
            <span>High</span>
          </div>
        </div>

        <div>
          <label style={{
            display: 'block',
            marginBottom: '0.5rem',
            fontSize: '0.95rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05rem',
            opacity: 0.9
          }}>
            Location
          </label>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="text"
              value={location ? `${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}` : 'Not set'}
              readOnly
              style={{
                flex: 1,
                padding: '0.75rem',
                borderRadius: '10px',
                border: '1px solid rgba(255,255,255,0.3)',
                background: 'rgba(15, 23, 42, 0.25)',
                color: 'white',
                fontSize: '0.9rem'
              }}
            />
            <button
              type="button"
              onClick={handleGetCurrentLocation}
              style={{
                padding: '0.75rem 1rem',
                borderRadius: '10px',
                border: '1px solid rgba(255,255,255,0.3)',
                background: 'rgba(15, 23, 42, 0.25)',
                color: 'white',
                cursor: 'pointer',
                fontSize: '0.9rem',
                whiteSpace: 'nowrap'
              }}
            >
              📡 Get Location
            </button>
          </div>
        </div>

        <div>
          <label style={{
            display: 'block',
            marginBottom: '0.5rem',
            fontSize: '0.95rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05rem',
            opacity: 0.9
          }}>
            Description (Optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Provide additional details about the condition..."
            rows={4}
            style={{
              width: '100%',
              padding: '0.75rem',
              borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.3)',
              background: 'rgba(15, 23, 42, 0.25)',
              color: 'white',
              fontSize: '0.9rem',
              resize: 'vertical',
              fontFamily: 'inherit'
            }}
          />
        </div>

        {message && (
          <div style={{
            padding: '0.75rem',
            borderRadius: '10px',
            background: message.includes('Error')
              ? 'rgba(244, 63, 94, 0.25)'
              : 'rgba(34, 197, 94, 0.25)',
            border: `1px solid ${message.includes('Error')
              ? 'rgba(244, 63, 94, 0.5)'
              : 'rgba(34, 197, 94, 0.5)'}`,
            fontSize: '0.9rem',
            textAlign: 'center'
          }}>
            {message}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          style={{
            padding: '0.95rem',
            borderRadius: '12px',
            border: 'none',
            background: isSubmitting
              ? 'rgba(148,163,184,0.5)'
              : 'linear-gradient(135deg, #22c55e, #16a34a)',
            color: 'white',
            fontSize: '1rem',
            fontWeight: 700,
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            boxShadow: isSubmitting ? 'none' : '0 12px 28px rgba(34,197,94,0.35)',
            transition: 'all 0.3s ease'
          }}
        >
          {isSubmitting ? 'Submitting...' : '✉️ Submit Feedback'}
        </button>
      </form>
    </div>
  );
}
