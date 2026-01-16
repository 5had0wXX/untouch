import React, { useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";

const DEFAULT_CENTER = [39.0997, -94.5786];
const DEFAULT_RADIUS = 15;

const glowIcon = L.divIcon({
  className: "lead-marker",
  html: "<span class='lead-marker__dot'></span>",
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

const placeholderLeads = [
  {
    id: "kc-1",
    name: "KCI Logistics Campus",
    type: "Intermodal",
    score: 92,
    lat: 39.3156,
    lng: -94.7139,
    date: "2024-08-09",
    signals: {
      newsHits: 12,
      powerOutages: 3,
      imageryFlags: ["Vacancy", "Heavy truck traffic"],
      zoningAlerts: 2
    },
    summary: "Strong infrastructure access with underutilized parcels."
  },
  {
    id: "kc-2",
    name: "West Bottoms Revamp",
    type: "Mixed-use",
    score: 86,
    lat: 39.1084,
    lng: -94.6036,
    date: "2024-07-22",
    signals: {
      newsHits: 8,
      powerOutages: 1,
      imageryFlags: ["Large vacant lot"],
      zoningAlerts: 1
    },
    summary: "Industrial corridor with renewal grants and active bids."
  },
  {
    id: "kc-3",
    name: "Independence Rail Yard",
    type: "Industrial",
    score: 79,
    lat: 39.0951,
    lng: -94.4211,
    date: "2024-06-14",
    signals: {
      newsHits: 5,
      powerOutages: 0,
      imageryFlags: ["Idle freight cars"],
      zoningAlerts: 0
    },
    summary: "Rail-adjacent site with large footprint and low utilization."
  }
];

function FlyToLocation({ center }) {
  const map = useMap();
  React.useEffect(() => {
    if (center) {
      map.flyTo(center, 12, { duration: 1.4 });
    }
  }, [center, map]);
  return null;
}

export default function App() {
  const [address, setAddress] = useState("");
  const [radius, setRadius] = useState(DEFAULT_RADIUS);
  const [leads, setLeads] = useState(placeholderLeads);
  const [selectedLead, setSelectedLead] = useState(placeholderLeads[0]);
  const [sortBy, setSortBy] = useState("score");
  const [filterType, setFilterType] = useState("all");
  const [chatOpen, setChatOpen] = useState(true);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([
    {
      role: "assistant",
      content:
        "Ask me about top P3 candidates. I can rank leads by score, signal strength, and proximity."
    }
  ]);
  const [mapCenter, setMapCenter] = useState(DEFAULT_CENTER);

  const filteredLeads = useMemo(() => {
    const subset = leads.filter((lead) =>
      filterType === "all" ? true : lead.type === filterType
    );
    return [...subset].sort((a, b) => {
      if (sortBy === "date") {
        return new Date(b.date) - new Date(a.date);
      }
      if (sortBy === "type") {
        return a.type.localeCompare(b.type);
      }
      return b.score - a.score;
    });
  }, [leads, sortBy, filterType]);

  const handleSearch = async (event) => {
    event.preventDefault();
    if (!address.trim()) {
      return;
    }
    try {
      const response = await fetch(
        `/api/geocode?address=${encodeURIComponent(address.trim())}`
      );
      if (!response.ok) {
        throw new Error("Geocode failed");
      }
      const data = await response.json();
      setMapCenter([data.lat, data.lng]);
      const leadResponse = await fetch(
        `/api/leads?lat=${data.lat}&lng=${data.lng}&radius=${radius}`
      );
      if (!leadResponse.ok) {
        throw new Error("Lead query failed");
      }
      const leadData = await leadResponse.json();
      setLeads(leadData);
      setSelectedLead(leadData[0]);
    } catch (error) {
      setLeads(placeholderLeads);
      setSelectedLead(placeholderLeads[0]);
    }
  };

  const handleChatSubmit = async (event) => {
    event.preventDefault();
    if (!chatInput.trim()) {
      return;
    }
    const userMessage = { role: "user", content: chatInput.trim() };
    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage.content })
      });
      if (!response.ok) {
        throw new Error("Chat failed");
      }
      const data = await response.json();
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response }
      ]);
    } catch (error) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I'm offline, but the highest-scoring lead right now is the KCI Logistics Campus at 92."
        }
      ]);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__pulse"></span>
          <div>
            <h1>P3 Site Finder</h1>
            <p>Identify high-potential sites with live signals.</p>
          </div>
        </div>

        <form className="search" onSubmit={handleSearch}>
          <label>
            Address or region
            <input
              type="text"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              placeholder="Enter city, address, or asset"
            />
          </label>
          <label>
            Search radius: {radius} mi
            <input
              type="range"
              min="5"
              max="100"
              value={radius}
              onChange={(event) => setRadius(Number(event.target.value))}
            />
          </label>
          <button type="submit">Scan for leads</button>
        </form>

        <div className="controls">
          <label>
            Sort by
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
              <option value="score">Score</option>
              <option value="date">Date</option>
              <option value="type">Site type</option>
            </select>
          </label>
          <label>
            Filter type
            <select
              value={filterType}
              onChange={(event) => setFilterType(event.target.value)}
            >
              <option value="all">All types</option>
              <option value="Intermodal">Intermodal</option>
              <option value="Mixed-use">Mixed-use</option>
              <option value="Industrial">Industrial</option>
            </select>
          </label>
        </div>

        <div className="lead-list">
          {filteredLeads.map((lead) => (
            <button
              type="button"
              key={lead.id}
              className={
                selectedLead?.id === lead.id ? "lead-card active" : "lead-card"
              }
              onClick={() => setSelectedLead(lead)}
            >
              <div className="lead-card__header">
                <h3>{lead.name}</h3>
                <span className="score">{lead.score}</span>
              </div>
              <div className="lead-card__meta">
                <span>{lead.type}</span>
                <span>{lead.date}</span>
              </div>
              <p>{lead.summary}</p>
            </button>
          ))}
        </div>
      </aside>

      <main className="map-area">
        <MapContainer center={mapCenter} zoom={11} className="map">
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution="&copy; OpenStreetMap contributors"
          />
          <FlyToLocation center={mapCenter} />
          {filteredLeads.map((lead) => (
            <Marker
              key={lead.id}
              position={[lead.lat, lead.lng]}
              icon={glowIcon}
              eventHandlers={{
                click: () => setSelectedLead(lead)
              }}
            >
              <Popup>
                <div className="popup">
                  <h3>{lead.name}</h3>
                  <p>{lead.summary}</p>
                  <div className="popup__tags">
                    <span>{lead.type}</span>
                    <span>Score {lead.score}</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        <section className="details">
          {selectedLead ? (
            <>
              <div className="details__header">
                <h2>{selectedLead.name}</h2>
                <span className="score">{selectedLead.score}</span>
              </div>
              <div className="details__meta">
                <span>{selectedLead.type}</span>
                <span>Updated {selectedLead.date}</span>
              </div>
              <p>{selectedLead.summary}</p>
              <div className="signal-grid">
                <div>
                  <h4>News hits</h4>
                  <span>{selectedLead.signals.newsHits}</span>
                </div>
                <div>
                  <h4>Power outages</h4>
                  <span>{selectedLead.signals.powerOutages}</span>
                </div>
                <div>
                  <h4>Imagery flags</h4>
                  <span>{selectedLead.signals.imageryFlags.join(", ")}</span>
                </div>
                <div>
                  <h4>Zoning alerts</h4>
                  <span>{selectedLead.signals.zoningAlerts}</span>
                </div>
              </div>
            </>
          ) : (
            <p>Select a lead to view signals.</p>
          )}
        </section>

        <div className={chatOpen ? "chat-widget open" : "chat-widget"}>
          <button type="button" onClick={() => setChatOpen(!chatOpen)}>
            {chatOpen ? "Hide" : "Ask GPT"}
          </button>
          {chatOpen && (
            <div className="chat-panel">
              <div className="chat-messages">
                {chatMessages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`chat-message ${message.role}`}
                  >
                    {message.content}
                  </div>
                ))}
              </div>
              <form onSubmit={handleChatSubmit}>
                <input
                  type="text"
                  placeholder="What's the best lead near Denver?"
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                />
                <button type="submit">Send</button>
              </form>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
