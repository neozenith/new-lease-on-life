import { useEffect, useRef, useState } from 'react';
import { GoogleMapsOverlay } from '@deck.gl/google-maps';
// import { GeoJsonLayer } from '@deck.gl/layers';
import './App.css'



interface Route {
  origin: string;
  destination: string;
  travel_mode: string;
  distance_meters: number;
  duration: string;
  // path_geojson?: GeoJSON.Feature | null;
}

// Google Maps + Deck.gl Map Component
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || (window as any).GOOGLE_MAPS_API_KEY;

function DeckGLGoogleMap({ routes }: { routes: Route[] }) {
  const mapRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<GoogleMapsOverlay | null>(null);

  useEffect(() => {
    if (!mapRef.current || !GOOGLE_MAPS_API_KEY) return;
    // Load Google Maps JS API (stable, v=quarterly)
    if (!document.querySelector('script[data-google-maps]')) {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=maps,places&v=quarterly`;
      script.async = true;
      script.setAttribute('data-google-maps', 'true');
      script.onload = () => {
        // @ts-ignore
        const google = window.google;
        if (!google || !mapRef.current) return;
        const map = new google.maps.Map(mapRef.current as HTMLElement, {
          center: { lat: -37.8136, lng: 144.9631 }, // Melbourne
          zoom: 11,
          mapId: 'DECK_GL_3D',
          tilt: 45,
          heading: 0,
          mapTypeId: 'hybrid',
        });
        overlayRef.current = new GoogleMapsOverlay({ layers: [] });
        overlayRef.current.setMap(map);
      };
      document.body.appendChild(script);
    } else {
      // If already loaded, initialize map immediately
      // @ts-ignore
      const google = window.google;
      if (!google || !mapRef.current) return;
      const map = new google.maps.Map(mapRef.current as HTMLElement, {
        center: { lat: -37.8136, lng: 144.9631 },
        zoom: 11,
        mapId: 'DECK_GL_3D',
        tilt: 45,
        heading: 0,
        mapTypeId: 'hybrid',
      });
      overlayRef.current = new GoogleMapsOverlay({ layers: [] });
      overlayRef.current.setMap(map);
    }
    return () => {
      if (overlayRef.current) overlayRef.current.setMap(null);
    };
  }, []);

  // Remove GeoJsonLayer effect for now
  // useEffect(() => {
  //   if (!overlayRef.current) return;
  //   const geojsonFeatures = routes
  //     .map(r => r.path_geojson)
  //     .filter(Boolean) as GeoJSON.Feature[];
  //   if (geojsonFeatures.length === 0) {
  //     overlayRef.current.setProps({ layers: [] });
  //     return;
  //   }
  //   const geojsonLayer = new GeoJsonLayer({
  //     id: 'routes-geojson',
  //     data: { type: 'FeatureCollection', features: geojsonFeatures },
  //     stroked: true,
  //     filled: false,
  //     getLineColor: [0, 128, 255, 180],
  //     getLineWidth: 4,
  //     pickable: true,
  //   });
  //   overlayRef.current.setProps({ layers: [geojsonLayer] });
  // }, [routes]);

  return (
    <div ref={mapRef} style={{ width: '100%', height: 500, marginBottom: 24, borderRadius: 8, overflow: 'hidden' }} />
  );
}

function App() {
  const [routes, setRoutes] = useState<Route[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('https://localhost:8000/api/routes')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch routes')
        return res.json()
      })
      .then(setRoutes)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: 16 }}>
      <h1>Route Visualizer</h1>
      <DeckGLGoogleMap routes={routes} />
      <h2>Routes</h2>
      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <table
        style={{
          width: '100%',
          marginTop: 16,
          borderCollapse: 'collapse',
        }}
      >
        <thead>
          <tr>
            <th>Origin</th>
            <th>Destination</th>
            <th>Mode</th>
            <th>Distance (km)</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          {routes.map((route, i) => (
            <tr key={i}>
              <td>{route.origin}</td>
              <td>{route.destination}</td>
              <td>{route.travel_mode}</td>
              <td>{(route.distance_meters / 1000).toFixed(2)}</td>
              <td>{route.duration}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default App
