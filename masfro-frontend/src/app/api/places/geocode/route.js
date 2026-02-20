import { NextResponse } from 'next/server';

const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export async function POST(request) {
  if (!GOOGLE_MAPS_API_KEY) {
    return NextResponse.json(
      { error: 'Google Maps API key is not configured.' },
      { status: 500 }
    );
  }

  try {
    const { address, components = 'country:PH' } = await request.json();

    if (!address || address.trim().length < 3) {
      return NextResponse.json({ status: 'ZERO_RESULTS', results: [] });
    }

    const params = new URLSearchParams({
      address: address.trim(),
      key: GOOGLE_MAPS_API_KEY,
      components,
    });

    const response = await fetch(
      `https://maps.googleapis.com/maps/api/geocode/json?${params.toString()}`,
      {
        method: 'GET',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        {
          error: data?.error_message || 'Geocoding request failed.',
          status: data?.status || 'UNKNOWN_ERROR',
        },
        { status: response.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Geocode API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch geocode results.' },
      { status: 500 }
    );
  }
}
