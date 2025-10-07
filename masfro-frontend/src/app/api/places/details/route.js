import { NextResponse } from 'next/server';

const GOOGLE_MAPS_API_KEY = process.env.GOOGLE_MAPS_API_KEY || process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export async function POST(request) {
  if (!GOOGLE_MAPS_API_KEY) {
    return NextResponse.json({ error: 'Google Maps API key is not configured.' }, { status: 500 });
  }

  try {
    const { placeId, sessionToken, fields = 'formatted_address,geometry/location,name' } = await request.json();

    if (!placeId) {
      return NextResponse.json({ error: 'Missing place ID.' }, { status: 400 });
    }

    if (!sessionToken) {
      return NextResponse.json({ error: 'Missing session token.' }, { status: 400 });
    }

    const params = new URLSearchParams({
      place_id: placeId,
      key: GOOGLE_MAPS_API_KEY,
      sessiontoken: sessionToken,
      fields,
    });

    const response = await fetch(
      `https://maps.googleapis.com/maps/api/place/details/json?${params.toString()}`,
      {
        method: 'GET',
        cache: 'no-store',
        headers: {
          'Accept': 'application/json',
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data?.error_message || 'Place details request failed.', status: data?.status || 'UNKNOWN_ERROR' },
        { status: response.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Place details API error:', error);
    return NextResponse.json({ error: 'Failed to fetch place details.' }, { status: 500 });
  }
}
