import React, { useState, useEffect } from 'react';
import { Users, Shield, Navigation, Radio } from 'lucide-react';

export default function TeamsPage() {
  const [teams, setTeams] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/teams')
      .then(res => res.json())
      .then(data => {
        if(Array.isArray(data)) setTeams(data);
      })
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="flex-1 overflow-auto bg-slate-100 p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Field Teams & Volunteers</h1>
          <p className="text-slate-500 text-sm">Monitor personnel deployed in disaster zones.</p>
        </div>
        <button className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-sm transition">
          Deploy New Team
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 border-b border-slate-200 uppercase text-xs font-semibold text-slate-500 tracking-wider">
            <tr>
              <th className="px-6 py-4">Team ID</th>
              <th className="px-6 py-4">Specialization</th>
              <th className="px-6 py-4">Size</th>
              <th className="px-6 py-4">Current Location</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4 text-right">Comms</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {teams.map((team) => (
              <tr key={team.id} className="hover:bg-slate-50 transition">
                <td className="px-6 py-4 font-bold text-slate-800 flex items-center">
                  <Shield size={16} className="mr-2 text-indigo-500" /> {team.id}
                </td>
                <td className="px-6 py-4 font-medium">{team.type}</td>
                <td className="px-6 py-4">{team.size} Personnel</td>
                <td className="px-6 py-4 flex items-center">
                  <Navigation size={14} className="mr-2 text-slate-400" /> {team.location}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                    team.status === 'Deployed' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {team.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="text-slate-400 hover:text-indigo-600 transition">
                    <Radio size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
