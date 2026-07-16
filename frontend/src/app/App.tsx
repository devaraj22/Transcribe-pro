import React, { useState } from 'react';
import { AppLayout } from '../components/layouts/AppLayout';
import { QuickCaptureView } from '../components/layouts/QuickCaptureView';
import { MeetingModeView } from '../components/layouts/MeetingModeView';

export default function App() {
  const [activeTab, setActiveTab] = useState('quick');

  return (
    <AppLayout activeTab={activeTab} setActiveTab={setActiveTab}>
      
      {/* Dynamic View Routing */}
      {activeTab === 'quick' && <QuickCaptureView />}
      {activeTab === 'meeting' && <MeetingModeView />}

    </AppLayout>
  );
}