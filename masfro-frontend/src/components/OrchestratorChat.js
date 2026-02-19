'use client';

import { useState, useRef, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

/**
 * OrchestratorChat Component
 *
 * Provides a natural language interface to the multi-agent orchestrator.
 * Users can type requests like:
 * - "What's the flood risk at Marikina Heights?"
 * - "Find me an evacuation route from Concepcion"
 * - "Calculate route from Tumana to Nangka"
 * - "Update risk levels across the city"
 */
export default function OrchestratorChat({ onRouteResult, startPoint }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [pollingMissions, setPollingMissions] = useState(new Set());
  const messagesEndRef = useRef(null);
  const pollIntervalsRef = useRef({});

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollIntervalsRef.current).forEach(clearInterval);
    };
  }, []);

  const addMessage = (role, content, meta = {}) => {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setMessages(prev => [...prev, { id, role, content, timestamp: new Date(), ...meta }]);
    return id;
  };

  const updateMessage = (id, updates) => {
    setMessages(prev => prev.map(msg => msg.id === id ? { ...msg, ...updates } : msg));
  };

  const pollMissionStatus = (missionId, msgId) => {
    if (pollIntervalsRef.current[missionId]) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/orchestrator/mission/${missionId}`);
        if (!res.ok) return;
        const data = await res.json();

        const rawState = data.fsm_state || data.state || '';
        const state = rawState.toLowerCase();

        if (state === 'completed' || state === 'failed' || state === 'timed_out') {
          clearInterval(interval);
          delete pollIntervalsRef.current[missionId];
          setPollingMissions(prev => {
            const next = new Set(prev);
            next.delete(missionId);
            return next;
          });

          // Fetch summary
          try {
            const summaryRes = await fetch(`${API_BASE}/api/orchestrator/mission/${missionId}/summary`);
            if (summaryRes.ok) {
              const summaryData = await summaryRes.json();
              const summaryText = summaryData.summary || summaryData.summary_text;
              if (summaryText) {
                updateMessage(msgId, {
                  content: summaryText,
                  state: state,
                  result: data.results
                });

                // If route result, pass to parent for map display
                // Results are keyed by agent ID (e.g. routing_agent_001)
                const routeResult = data.results;
                let routeData = null;
                if (routeResult?.path) {
                  routeData = routeResult;
                } else if (routeResult && typeof routeResult === 'object') {
                  // Search through agent result values for route data
                  for (const val of Object.values(routeResult)) {
                    if (val?.route?.path) {
                      routeData = val.route;
                      break;
                    } else if (val?.path) {
                      routeData = val;
                      break;
                    }
                  }
                }
                if (routeData?.path && onRouteResult) {
                  onRouteResult(routeData);
                }
                return;
              }
            }
          } catch (e) {
            // Fallback to raw result
          }

          // Fallback: show raw result
          const resultText = state === 'completed'
            ? `Mission completed. ${JSON.stringify(data.results || {}).substring(0, 300)}`
            : `Mission ${state}. ${data.error || ''}`.trim();
          updateMessage(msgId, { content: resultText, state: state, result: data.results });
        } else {
          // Update progress
          updateMessage(msgId, {
            content: `Processing... (${state})`,
            state: state
          });
        }
      } catch (err) {
        // Silently retry
      }
    }, 2000);

    pollIntervalsRef.current[missionId] = interval;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    addMessage('user', userMessage);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/orchestrator/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          user_location: startPoint ? { lat: startPoint.lat, lng: startPoint.lng } : null,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Server error' }));
        addMessage('assistant', `Error: ${errData.detail || res.statusText}`, { isError: true });
        return;
      }

      const data = await res.json();

      // Handle off-topic rejection
      if (data.status === 'off_topic') {
        const reason = data.interpretation?.message || 'This query is outside my scope. I only handle flood routing, risk assessment, and evacuation for Marikina City.';
        addMessage('assistant', reason, { isOffTopic: true });
        return;
      }

      // Handle clarification questions
      if (data.status === 'needs_clarification') {
        const question = data.message || data.interpretation?.message || 'Could you provide more details?';
        addMessage('assistant', question);
        return;
      }

      const missionId = data.mission?.mission_id;
      const missionType = data.mission?.type || data.interpretation?.mission_type;

      if (missionId) {
        const reasoning = data.interpretation?.reasoning;
        const startText = reasoning
          ? `${reasoning}\n\nStarting ${missionType || 'mission'}...`
          : `Starting mission: ${missionType || 'processing'}...`;

        const msgId = addMessage('assistant', startText, {
          missionId: missionId,
          missionType: missionType,
          state: 'starting'
        });

        setPollingMissions(prev => new Set(prev).add(missionId));
        pollMissionStatus(missionId, msgId);
      } else if (data.status === 'error') {
        const errorMsg = data.interpretation?.message || data.interpretation?.error || data.message || 'Could not process request.';
        addMessage('assistant', errorMsg, { isError: true });
      } else {
        addMessage('assistant', data.message || 'Request received.');
      }
    } catch (err) {
      addMessage('assistant', `Connection error: ${err.message}. Is the backend running?`, { isError: true });
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await fetch(`${API_BASE}/api/orchestrator/chat/clear`, { method: 'POST' });
    } catch (e) {
      // Backend clear failed, still clear frontend
    }
    setMessages([]);
    // Clear any active polling
    Object.values(pollIntervalsRef.current).forEach(clearInterval);
    pollIntervalsRef.current = {};
    setPollingMissions(new Set());
  };

  const getStateColor = (state) => {
    if (state === 'completed') return '#22c55e';
    if (state === 'failed' || state === 'timed_out') return '#ef4444';
    return '#f59e0b';
  };

  const getStateIcon = (state) => {
    if (state === 'completed') return '[OK]';
    if (state === 'failed' || state === 'timed_out') return '[FAIL]';
    return '...';
  };

  const suggestions = [
    "What's the flood risk at Tumana?",
    "Route from Concepcion to Nangka",
    "Find evacuation center near Malanday",
    "Update risk levels citywide",
  ];

  return (
    <div className={`orchestrator-chat ${isCollapsed ? 'collapsed' : ''}`}>
      <style jsx>{`
        .orchestrator-chat {
          position: relative;
          width: 100%;
          min-height: 350px;
          background: linear-gradient(160deg, rgba(15, 20, 25, 0.95) 0%, rgba(30, 35, 40, 0.95) 100%);
          backdrop-filter: blur(16px);
          border-radius: 16px;
          border: 1px solid rgba(139, 92, 246, 0.3);
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .orchestrator-chat.collapsed {
          min-height: auto;
          max-height: 80px;
        }

        .chat-header {
          padding: 1.25rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(139, 92, 246, 0.1);
          cursor: pointer;
          user-select: none;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .chat-header:hover {
          background: rgba(139, 92, 246, 0.15);
        }

        .header-content {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .chat-icon {
          font-size: 1.25rem;
        }

        .chat-title {
          font-size: 1rem;
          font-weight: 700;
          color: white;
          margin: 0;
          letter-spacing: 0.5px;
        }

        .chat-subtitle {
          font-size: 0.7rem;
          color: rgba(139, 92, 246, 0.8);
          margin-top: 0.15rem;
        }

        .collapse-btn {
          background: rgba(139, 92, 246, 0.2);
          border: 1px solid rgba(139, 92, 246, 0.4);
          border-radius: 8px;
          padding: 0.5rem;
          color: white;
          cursor: pointer;
          font-size: 1rem;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 32px;
          min-height: 32px;
        }

        .collapse-btn:hover {
          background: rgba(139, 92, 246, 0.3);
          transform: scale(1.05);
        }

        .messages-area {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          min-height: 0;
        }

        .message {
          max-width: 90%;
          padding: 0.75rem 1rem;
          border-radius: 12px;
          font-size: 0.85rem;
          line-height: 1.5;
          word-break: break-word;
          animation: fadeIn 0.3s ease-out;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(5px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
          align-self: flex-end;
          background: rgba(139, 92, 246, 0.3);
          border: 1px solid rgba(139, 92, 246, 0.4);
          color: white;
        }

        .message.assistant {
          align-self: flex-start;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.9);
        }

        .message.error {
          border-color: rgba(239, 68, 68, 0.4);
          background: rgba(239, 68, 68, 0.1);
          color: #fca5a5;
        }

        .message.off-topic {
          border-color: rgba(251, 191, 36, 0.4);
          background: rgba(251, 191, 36, 0.1);
          color: #fde68a;
          font-style: italic;
        }

        .mission-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          font-size: 0.65rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 0.5rem;
        }

        .msg-time {
          font-size: 0.6rem;
          opacity: 0.5;
          margin-top: 0.25rem;
        }

        .suggestions {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .suggestion-btn {
          padding: 0.4rem 0.75rem;
          border-radius: 20px;
          border: 1px solid rgba(139, 92, 246, 0.3);
          background: rgba(139, 92, 246, 0.1);
          color: rgba(139, 92, 246, 0.9);
          font-size: 0.7rem;
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
        }

        .suggestion-btn:hover {
          background: rgba(139, 92, 246, 0.2);
          border-color: rgba(139, 92, 246, 0.5);
          transform: translateY(-1px);
        }

        .input-area {
          padding: 0.75rem 1rem;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          gap: 0.5rem;
        }

        .chat-input {
          flex: 1;
          padding: 0.75rem 1rem;
          border-radius: 12px;
          border: 1px solid rgba(139, 92, 246, 0.3);
          background: rgba(139, 92, 246, 0.05);
          color: white;
          font-size: 0.85rem;
          outline: none;
          transition: border-color 0.2s;
          font-family: inherit;
        }

        .chat-input:focus {
          border-color: rgba(139, 92, 246, 0.6);
        }

        .chat-input::placeholder {
          color: rgba(255, 255, 255, 0.3);
        }

        .send-btn {
          padding: 0.75rem 1.25rem;
          border-radius: 12px;
          border: none;
          background: linear-gradient(135deg, rgba(139, 92, 246, 0.8), rgba(109, 40, 217, 0.8));
          color: white;
          font-weight: 700;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .send-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
        }

        .send-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .clear-btn {
          padding: 0.5rem 0.75rem;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.15);
          background: rgba(255, 255, 255, 0.05);
          color: rgba(255, 255, 255, 0.5);
          font-size: 0.7rem;
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
        }

        .clear-btn:hover {
          background: rgba(239, 68, 68, 0.15);
          border-color: rgba(239, 68, 68, 0.3);
          color: #fca5a5;
        }

        .empty-state {
          text-align: center;
          padding: 2rem 1rem;
          color: rgba(255, 255, 255, 0.4);
        }

        .empty-state .icon {
          font-size: 2rem;
          margin-bottom: 0.5rem;
        }

        .empty-state p {
          font-size: 0.8rem;
          margin: 0.25rem 0;
        }

        ::-webkit-scrollbar {
          width: 6px;
        }

        ::-webkit-scrollbar-track {
          background: transparent;
        }

        ::-webkit-scrollbar-thumb {
          background: rgba(139, 92, 246, 0.3);
          border-radius: 10px;
        }

        @media (max-width: 767px) {
          .orchestrator-chat {
            min-height: 0;
            max-height: calc(70vh - 56px);
            border-radius: 0;
          }
        }
      `}</style>

      {/* Header */}
      <div className="chat-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="header-content">
          <span className="chat-icon">🧠</span>
          <div>
            <h2 className="chat-title">AI ORCHESTRATOR</h2>
            <div className="chat-subtitle">Natural Language Agent Control</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {messages.length > 0 && !isCollapsed && (
            <button
              className="clear-btn"
              onClick={(e) => { e.stopPropagation(); handleClearHistory(); }}
              title="Clear chat history"
            >
              Clear
            </button>
          )}
          <button
            className="collapse-btn"
            onClick={(e) => { e.stopPropagation(); setIsCollapsed(!isCollapsed); }}
            title={isCollapsed ? "Expand" : "Collapse"}
          >
            {isCollapsed ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Messages */}
          <div className="messages-area">
            {messages.length === 0 && (
              <div className="empty-state">
                <div className="icon">🤖</div>
                <p>Ask me anything about flood conditions,</p>
                <p>routing, or evacuation in Marikina City.</p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`message ${msg.role} ${msg.isError ? 'error' : ''} ${msg.isOffTopic ? 'off-topic' : ''}`}
              >
                {msg.missionId && msg.state && (
                  <div
                    className="mission-badge"
                    style={{
                      background: `${getStateColor(msg.state)}22`,
                      color: getStateColor(msg.state),
                      border: `1px solid ${getStateColor(msg.state)}44`
                    }}
                  >
                    {getStateIcon(msg.state)} {msg.missionType || 'mission'}
                  </div>
                )}
                <div>{msg.content}</div>
                <div className="msg-time">
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions (only show when no messages) */}
          {messages.length === 0 && (
            <div className="suggestions">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  className="suggestion-btn"
                  onClick={() => setInput(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <form className="input-area" onSubmit={handleSubmit}>
            <input
              type="text"
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about flood risk, routes, evacuations..."
              disabled={isLoading}
            />
            <button
              type="submit"
              className="send-btn"
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? '...' : 'Send'}
            </button>
          </form>
        </>
      )}
    </div>
  );
}
