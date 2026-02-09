import { NextResponse } from "next/server";

const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export async function POST(request) {
  if (!GOOGLE_MAPS_API_KEY) {
    return NextResponse.json(
      { error: "Google Maps API key is not configured." },
      { status: 500 },
    );
  }

  try {
    const {
      input,
      sessionToken,
      components = "country:ph",
    } = await request.json();

    if (!input || input.trim().length < 3) {
      return NextResponse.json({ status: "ZERO_RESULTS", predictions: [] });
    }

    if (!sessionToken) {
      return NextResponse.json(
        { error: "Missing session token." },
        { status: 400 },
      );
    }

    const params = new URLSearchParams({
      input,
      key: GOOGLE_MAPS_API_KEY,
      sessiontoken: sessionToken,
      components,
    });

    const response = await fetch(
      `https://maps.googleapis.com/maps/api/place/autocomplete/json?${params.toString()}`,
      {
        method: "GET",
        cache: "no-store",
        headers: {
          Accept: "application/json",
        },
      },
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        {
          error: data?.error_message || "Autocomplete request failed.",
          status: data?.status || "UNKNOWN_ERROR",
        },
        { status: response.status },
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error("Autocomplete API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch autocomplete results." },
      { status: 500 },
    );
  }
}
