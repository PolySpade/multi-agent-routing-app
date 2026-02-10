'use client';

import { useState, useEffect, useRef, useMemo } from 'react';

const LocationSearch = ({ onLocationSelect, placeholder = "Search for a location...", type = "start" }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchTimeout = useRef(null);
  const dropdownRef = useRef(null);
  const sessionTokenRef = useRef(null);

  const ensureSessionToken = () => {
    if (!sessionTokenRef.current) {
      try {
        const cryptoRef = typeof window !== 'undefined' ? window.crypto : undefined;
        if (cryptoRef?.randomUUID) {
          sessionTokenRef.current = cryptoRef.randomUUID();
          return;
        }
      } catch (error) {
        // ignore and fallback
      }
      sessionTokenRef.current = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    }
  };

  useEffect(() => {
    ensureSessionToken();
  }, []);

  const clearSessionToken = () => {
    sessionTokenRef.current = null;
    ensureSessionToken();
  };

  const headers = useMemo(() => ({
    'Content-Type': 'application/json',
  }), []);

  // Search locations using Mapbox Geocoding API
  const searchLocations = async (searchQuery) => {
    if (!searchQuery.trim() || searchQuery.length < 3) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);
    ensureSessionToken();

    try {
      const response = await fetch('/api/places/autocomplete', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          input: searchQuery,
          sessionToken: sessionTokenRef.current,
        }),
      });

      if (response.ok) {
        const data = await response.json();

        if (data.status === 'OK') {
          setSuggestions(data.predictions || []);
          setShowDropdown(true);
        } else {
          console.warn('Autocomplete response status:', data.status, data.error_message);
          setSuggestions([]);
        }
      } else {
        const errorData = await response.json().catch(() => null);
        console.warn('Autocomplete error response:', errorData);
        setSuggestions([]);
      }
    } catch (error) {
      console.error('Error searching locations:', error);
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle input change with debouncing
  const handleInputChange = (e) => {
    const value = e.target.value;
    setQuery(value);

    // Clear previous timeout
    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }

    // Set new timeout for search
    searchTimeout.current = setTimeout(() => {
      searchLocations(value);
    }, 300);
  };

  // Handle suggestion selection
  const handleSuggestionClick = async (suggestion) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/places/details', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          placeId: suggestion.place_id,
          sessionToken: sessionTokenRef.current,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'OK' && data.result) {
          const { formatted_address, geometry, name } = data.result;
          const location = geometry?.location;

          if (location && onLocationSelect) {
            onLocationSelect({
              lat: location.lat,
              lng: location.lng,
              name: name || suggestion.description,
              address: formatted_address,
            });
          }

          setQuery(formatted_address || suggestion.description || '');
          clearSessionToken();
        } else {
          console.warn('Place details status:', data.status, data.error_message);
        }
      } else {
        const errorData = await response.json().catch(() => null);
        console.warn('Place details error response:', errorData);
      }
    } catch (error) {
      console.error('Error fetching place details:', error);
    } finally {
      setSuggestions([]);
      setShowDropdown(false);
      setIsLoading(false);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const inputIcon = type === 'start' ? '📍' : '🎯';
  const inputColor = type === 'start' ? '#10b981' : '#ef4444';

  return (
    <div style={{ position: 'relative', width: '100%' }} ref={dropdownRef}>
      <div style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center'
      }}>
        <span style={{
          position: 'absolute',
          left: '12px',
          fontSize: '16px',
          zIndex: 1
        }}>
          {inputIcon}
        </span>
        
        <input
          type="text"
          value={query}
          onChange={handleInputChange}
          placeholder={placeholder}
          style={{
            width: '100%',
            padding: '12px 12px 12px 40px',
            borderRadius: '8px',
            border: `2px solid ${inputColor}20`,
            background: 'rgba(255, 255, 255, 0.9)',
            color: '#374151',
            fontSize: '14px',
            fontWeight: '500',
            outline: 'none',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)'
          }}
          onFocus={() => {
            if (suggestions.length > 0) {
              setShowDropdown(true);
            }
          }}
        />
        
        {isLoading && (
          <div style={{
            position: 'absolute',
            right: '12px',
            width: '16px',
            height: '16px',
            border: `2px solid ${inputColor}30`,
            borderTop: `2px solid ${inputColor}`,
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
        )}
      </div>

      {showDropdown && suggestions.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(10px)',
          borderRadius: '8px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
          zIndex: 50,
          maxHeight: '280px',
          overflowY: 'auto',
          marginTop: '4px',
          border: '1px solid rgba(255, 255, 255, 0.3)'
        }}>
          {suggestions.map((suggestion, index) => (
            <div
              key={suggestion.place_id || index}
              onClick={() => handleSuggestionClick(suggestion)}
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                borderBottom: index < suggestions.length - 1 ? '1px solid rgba(0, 0, 0, 0.1)' : 'none',
                transition: 'background-color 0.2s ease',
                fontSize: '14px',
                color: '#374151'
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = 'transparent';
              }}
            >
              <div style={{ fontWeight: '500', marginBottom: '2px' }}>
                {suggestion.structured_formatting?.main_text || suggestion.description}
              </div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>
                {suggestion.structured_formatting?.secondary_text || suggestion.description}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LocationSearch;
