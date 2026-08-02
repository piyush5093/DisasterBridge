import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Dashboard/Sidebar';
import Dashboard from './pages/Dashboard/Dashboard';
import MapView from './pages/MapView/MapView';
import Zones from './pages/Zones/Zones';
import Resources from './pages/Resources/Resources';
import Depots from './pages/Depots/Depots';
import Teams from './pages/Teams/Teams';
import LiveFeed from './pages/LiveFeed/LiveFeed';
import Allocation from './pages/Allocation/Allocation';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/map"        element={<MapView />} />
            <Route path="/zones"      element={<Zones />} />
            <Route path="/resources"  element={<Resources />} />
            <Route path="/depots"     element={<Depots />} />
            <Route path="/teams"      element={<Teams />} />
            <Route path="/feed"       element={<LiveFeed />} />
            <Route path="/allocation" element={<Allocation />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
