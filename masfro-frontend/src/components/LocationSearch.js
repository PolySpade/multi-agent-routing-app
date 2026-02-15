'use client';

import { useState, useEffect, useRef } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

const LocationSearch = ({ onLocationSelect, placeholder = "Search for a location...", type = "start" }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [error, setError] = useState(null);
  const errorTimeout = useRef(null);
  const searchTimeout = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    return () => {
      if (errorTimeout.current) clearTimeout(errorTimeout.current);
      if (searchTimeout.current) clearTimeout(searchTimeout.current);
    };
  }, []);

  const showError = (message) => {
    if (errorTimeout.current) clearTimeout(errorTimeout.current);
    setError(message);
    errorTimeout.current = setTimeout(() => setError(null), 5000);
  };

  // Search locations using Google Geocoding API (single call — returns coordinates directly)
  const searchLocations = async (searchQuery) => {
    if (!searchQuery.trim() || searchQuery.length < 3) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/places/geocode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: searchQuery }),
      });

      if (response.ok) {
        const data = await response.json();

        if (data.status === 'OK' && data.results?.length > 0) {
          setSuggestions(data.results);
          setShowDropdown(true);
        } else {
          setSuggestions([]);
        }
      } else {
        showError('Location search failed. Please try again.');
        setSuggestions([]);
      }
    } catch (error) {
      console.error('Error searching locations:', error);
      showError('Unable to search locations. Check your connection.');
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle input change with debouncing
  const handleInputChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    if (error) setError(null);

    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }

    searchTimeout.current = setTimeout(() => {
      searchLocations(value);
    }, 300);
  };

  // Handle suggestion selection — coordinates already available, no second API call needed
  const handleSuggestionClick = (result) => {
    const location = result.geometry?.location;

    if (location && onLocationSelect) {
      onLocationSelect({
        lat: location.lat,
        lng: location.lng,
        name: result.formatted_address,
        address: result.formatted_address,
      });
    }

    setQuery(result.formatted_address || '');
    setSuggestions([]);
    setShowDropdown(false);
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

  // Extract a short name from address components
  const getShortName = (result) => {
    const components = result.address_components || [];
    // Try to find a meaningful short name: establishment > route > neighborhood > sublocality
    for (const type of ['establishment', 'point_of_interest', 'route', 'neighborhood', 'sublocality_level_1', 'sublocality', 'locality']) {
      const match = components.find(c => c.types.includes(type));
      if (match) return match.long_name;
    }
    return result.formatted_address?.split(',')[0] || result.formatted_address;
  };

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

      {error && (
        <div style={{
          marginTop: '4px',
          padding: '8px 12px',
          borderRadius: '6px',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#ef4444',
          fontSize: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span style={{ fontSize: '14px' }}>!</span>
          {error}
        </div>
      )}

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
          {suggestions.map((result, index) => (
            <div
              key={result.place_id || index}
              onClick={() => handleSuggestionClick(result)}
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
                {getShortName(result)}
              </div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>
                {result.formatted_address}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LocationSearch;
