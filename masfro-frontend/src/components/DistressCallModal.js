'use client';

import { useState, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

const URGENCY_LEVELS = [
  { value: 'critical', label: 'CRITICAL', color: '#ef4444', desc: 'Life-threatening' },
  { value: 'high', label: 'HIGH', color: '#f97316', desc: 'Immediate danger' },
  { value: 'medium', label: 'MEDIUM', color: '#eab308', desc: 'Need assistance' },
  { value: 'low', label: 'LOW', color: '#22c55e', desc: 'Precautionary' },
];

export default function DistressCallModal({ onClose, onRouteResult }) {
  const [urgency, setUrgency] = useState('high');
  const [location, setLocation] = useState(null);
  const [locationText, setLocationText] = useState('');
  const [messageText, setMessageText] = useState('');
  const [context, setContext] = useState({ injuries: false, children: false, elderly: false, mobility: false });
  const [status, setStatus] = useState('idle'); // idle | locating | submitting | polling | done | error
  const [statusMsg, setStatusMsg] = useState('');
  const [missionResult, setMissionResult] = useState(null);

  const handleGetLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setStatusMsg('Geolocation not supported.');
      return;
    }
    setStatus('locating');
    setStatusMsg('Getting your location...');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setLocationText(`${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)}`);
        setStatus('idle');
        setStatusMsg('Location acquired.');
      },
      () => {
        setStatus('idle');
        setStatusMsg('Could not get location. Enter manually.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  const handleToggleContext = (key) => {
    setContext((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmit = async () => {
    if (!location) {
      setStatusMsg('Please set your location first.');
      return;
    }

    setStatus('submitting');
    setStatusMsg('Sending distress call...');

    const contextTags = Object.entries(context).filter(([, v]) => v).map(([k]) => k);
    const params = {
      location: [location.lat, location.lng],
      urgency,
      message: messageText.trim() || `Distress call - urgency: ${urgency}`,
      context_tags: contextTags,
    };

    try {
      const res = await fetch(`${API_BASE}/api/orchestrator/mission`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mission_type: 'coordinated_evacuation', params }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Mission creation failed');
      }

      const data = await res.json();
      const missionId = data.mission_id;

      setStatus('polling');
      setStatusMsg('Mission started. Waiting for agents...');

      // Poll for completion
      let attempts = 0;
      const maxAttempts = 30;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await fetch(`${API_BASE}/api/orchestrator/mission/${missionId}`);
          const missionData = await statusRes.json();

          if (missionData.state === 'COMPLETED' || missionData.state === 'completed') {
            clearInterval(poll);
            setMissionResult(missionData);
            setStatus('done');
            setStatusMsg('Evacuation plan ready!');

            // If route path exists, pass to parent
            const result = missionData.results || missionData.result;
            if (result?.route?.path && onRouteResult) {
              onRouteResult(result.route);
            }
          } else if (missionData.state === 'FAILED' || missionData.state === 'failed') {
            clearInterval(poll);
            setStatus('error');
            setStatusMsg(`Mission failed: ${missionData.error || 'Unknown error'}`);
          } else if (attempts >= maxAttempts) {
            clearInterval(poll);
            setStatus('error');
            setStatusMsg('Timed out waiting for response. Check missions panel.');
          } else {
            setStatusMsg(`Coordinating agents... (${missionData.state || 'processing'})`);
          }
        } catch {
          if (attempts >= maxAttempts) {
            clearInterval(poll);
            setStatus('error');
            setStatusMsg('Connection lost while polling.');
          }
        }
      }, 2000);
    } catch (err) {
      setStatus('error');
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  const selectedUrgency = URGENCY_LEVELS.find((u) => u.value === urgency);

  return (
    <div style={{
      background: 'linear-gradient(160deg, rgba(180, 40, 30, 0.95) 0%, rgba(120, 30, 20, 0.95) 50%, rgba(60, 15, 10, 0.98) 100%)',
      borderRadius: '18px',
      padding: '2rem',
      color: 'white',
      maxWidth: '520px',
      width: '100%',
      boxShadow: '0 20px 60px rgba(0, 0, 0, 0.6), 0 0 40px rgba(239, 68, 68, 0.2)',
      border: '1px solid rgba(239, 68, 68, 0.4)',
      maxHeight: '90vh',
      overflowY: 'auto',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800 }}>
            SOS DISTRESS CALL
          </h2>
          <div style={{ fontSize: '0.8rem', opacity: 0.8, marginTop: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Emergency Evacuation Request
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            background: 'rgba(0, 0, 0, 0.3)', border: '1px solid rgba(255,255,255,0.2)',
            color: 'white', borderRadius: '50%', width: '36px', height: '36px',
            cursor: 'pointer', fontSize: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            x
          </button>
        )}
      </div>

      {/* Urgency Selector */}
      <div style={{ marginBottom: '1.25rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
          Urgency Level
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
          {URGENCY_LEVELS.map((u) => (
            <button
              key={u.value}
              onClick={() => setUrgency(u.value)}
              style={{
                padding: '0.6rem 0.25rem',
                borderRadius: '10px',
                border: urgency === u.value ? `2px solid ${u.color}` : '1px solid rgba(255,255,255,0.15)',
                background: urgency === u.value ? `${u.color}33` : 'rgba(0,0,0,0.2)',
                color: urgency === u.value ? u.color : 'rgba(255,255,255,0.7)',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.2s',
                fontWeight: 700,
                fontSize: '0.7rem',
              }}
            >
              <div>{u.label}</div>
              <div style={{ fontSize: '0.6rem', fontWeight: 400, marginTop: '0.15rem', opacity: 0.8 }}>{u.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Location */}
      <div style={{ marginBottom: '1.25rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
          Your Location
        </label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={locationText}
            onChange={(e) => {
              setLocationText(e.target.value);
              // Try parse "lat, lng"
              const parts = e.target.value.split(',').map((s) => parseFloat(s.trim()));
              if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                setLocation({ lat: parts[0], lng: parts[1] });
              }
            }}
            placeholder="lat, lng"
            style={{
              flex: 1, padding: '0.75rem', borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(0,0,0,0.25)',
              color: 'white', fontSize: '0.9rem',
            }}
          />
          <button
            type="button"
            onClick={handleGetLocation}
            disabled={status === 'locating'}
            style={{
              padding: '0.75rem 1rem', borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(0,0,0,0.25)',
              color: 'white', cursor: 'pointer', fontSize: '0.85rem', whiteSpace: 'nowrap',
            }}
          >
            {status === 'locating' ? '...' : 'Use GPS'}
          </button>
        </div>
      </div>

      {/* Situation Description */}
      <div style={{ marginBottom: '1.25rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
          Situation
        </label>
        <textarea
          value={messageText}
          onChange={(e) => setMessageText(e.target.value)}
          placeholder="Describe your situation... (e.g., water rising fast, trapped on 2nd floor)"
          rows={3}
          style={{
            width: '100%', padding: '0.75rem', borderRadius: '10px',
            border: '1px solid rgba(255,255,255,0.25)', background: 'rgba(0,0,0,0.25)',
            color: 'white', fontSize: '0.9rem', resize: 'vertical', fontFamily: 'inherit',
          }}
        />
      </div>

      {/* Context Checkboxes */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
          People Involved
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
          {[
            { key: 'injuries', label: 'Injuries Present' },
            { key: 'children', label: 'With Children' },
            { key: 'elderly', label: 'Elderly Persons' },
            { key: 'mobility', label: 'Mobility Impaired' },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => handleToggleContext(item.key)}
              style={{
                padding: '0.6rem 0.75rem',
                borderRadius: '8px',
                border: context[item.key] ? '1px solid rgba(239, 68, 68, 0.6)' : '1px solid rgba(255,255,255,0.15)',
                background: context[item.key] ? 'rgba(239, 68, 68, 0.2)' : 'rgba(0,0,0,0.2)',
                color: context[item.key] ? '#fca5a5' : 'rgba(255,255,255,0.7)',
                cursor: 'pointer',
                textAlign: 'left',
                fontSize: '0.85rem',
                fontWeight: context[item.key] ? 600 : 400,
                transition: 'all 0.2s',
              }}
            >
              {context[item.key] ? '[x] ' : '[ ] '}{item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Status Message */}
      {statusMsg && (
        <div style={{
          padding: '0.75rem',
          borderRadius: '10px',
          background: status === 'error' ? 'rgba(239, 68, 68, 0.25)' : status === 'done' ? 'rgba(34, 197, 94, 0.25)' : 'rgba(255,255,255,0.1)',
          border: `1px solid ${status === 'error' ? 'rgba(239,68,68,0.5)' : status === 'done' ? 'rgba(34,197,94,0.5)' : 'rgba(255,255,255,0.2)'}`,
          fontSize: '0.9rem',
          textAlign: 'center',
          marginBottom: '1rem',
        }}>
          {statusMsg}
        </div>
      )}

      {/* Mission Result */}
      {missionResult && status === 'done' && (
        <div style={{
          padding: '1rem',
          borderRadius: '10px',
          background: 'rgba(34, 197, 94, 0.15)',
          border: '1px solid rgba(34, 197, 94, 0.4)',
          marginBottom: '1rem',
          fontSize: '0.85rem',
          lineHeight: 1.5,
        }}>
          <div style={{ fontWeight: 700, marginBottom: '0.5rem', color: '#4ade80' }}>
            Evacuation Plan Ready
          </div>
          {missionResult.results?.evacuation_center && (
            <div>Center: {missionResult.results.evacuation_center}</div>
          )}
          {missionResult.results?.route?.distance && (
            <div>Distance: {(missionResult.results.route.distance / 1000).toFixed(1)} km</div>
          )}
          {missionResult.results?.instructions && (
            <div style={{ marginTop: '0.5rem', opacity: 0.9 }}>
              {missionResult.results.instructions}
            </div>
          )}
        </div>
      )}

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={status === 'submitting' || status === 'polling' || status === 'locating'}
        style={{
          width: '100%',
          padding: '1rem',
          borderRadius: '12px',
          border: 'none',
          background: (status === 'submitting' || status === 'polling')
            ? 'rgba(148,163,184,0.5)'
            : `linear-gradient(135deg, ${selectedUrgency.color}, ${selectedUrgency.color}cc)`,
          color: 'white',
          fontSize: '1.1rem',
          fontWeight: 800,
          cursor: (status === 'submitting' || status === 'polling') ? 'not-allowed' : 'pointer',
          boxShadow: (status === 'submitting' || status === 'polling') ? 'none' : `0 8px 24px ${selectedUrgency.color}44`,
          transition: 'all 0.3s',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}
      >
        {status === 'submitting' ? 'SENDING...' : status === 'polling' ? 'PROCESSING...' : 'SEND DISTRESS CALL'}
      </button>
    </div>
  );
}
