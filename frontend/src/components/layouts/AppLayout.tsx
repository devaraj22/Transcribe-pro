import React, { ReactNode, useState } from 'react';
import { Cpu, Mic, Layers, History } from 'lucide-react';

import { HistoryPanel } from '../ui/HistoryPanel';

interface AppLayoutProps {
  children: ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, activeTab, setActiveTab }) => {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  return (
    <div className="app-container">
      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div>
          <div className="sidebar-header">
            <div className="logo-box">
              <Cpu size={20} />
            </div>
            <div className="logo-text">
              <h1>VoiceScribe AI</h1>
              <p>Industrial Engine</p>
            </div>
          </div>

          <nav className="sidebar-nav">
            <button
              onClick={() => setActiveTab('quick')}
              className={`nav-btn ${activeTab === 'quick' ? 'active' : ''}`}
            >
              <Mic size={18} />
              Quick Capture
            </button>

            <button
              onClick={() => setActiveTab('meeting')}
              className={`nav-btn ${activeTab === 'meeting' ? 'active' : ''}`}
            >
              <Layers size={18} />
              Meeting Mode
            </button>

            <button
              onClick={() => setIsHistoryOpen(true)}
              className="nav-btn"
            >
              <History size={18} />
              Job History Logs
            </button>
          </nav>
        </div>

      </aside>

      <main className="main-wrapper">
        <header className="top-header">
          <div className="breadcrumb">
            <span className="breadcrumb-label"></span>
            <span className="breadcrumb-current">{activeTab} view</span>
          </div>
        </header>

        <div className="workspace-content">
          {children}
        </div>
      </main>

      {/* Sliding History Drawer Component Container */}
      <HistoryPanel 
        isOpen={isHistoryOpen} 
        onClose={() => setIsHistoryOpen(false)} 
        onSelectJob={(jobId) => {
          console.log("Selected job ID:", jobId);
        }}
      />
    </div>
  );
};