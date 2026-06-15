import { useEffect } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import { CaptureProvider, useCapture } from './CaptureContext';
import Home from './Home';
import Consent from './Consent';
import Recording from './Recording';
import Upload from './Upload';
import QuickTag from './QuickTag';
import Confirm from './Confirm';
import Sent from './Sent';
import './capture.css';

function CaptureRoutes() {
  const { loadFamilyData, audio, storyId } = useCapture();

  useEffect(() => {
    loadFamilyData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      <Route index element={<Home />} />
      <Route path="consent" element={<Consent />} />
      <Route path="record" element={storyId ? <Recording /> : <Navigate to=".." replace />} />
      <Route path="upload" element={storyId ? <Upload /> : <Navigate to=".." replace />} />
      <Route path="tag" element={storyId ? <QuickTag /> : <Navigate to=".." replace />} />
      <Route path="confirm" element={audio ? <Confirm /> : <Navigate to=".." replace />} />
      <Route path="sent" element={<Sent />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  );
}

export default function CaptureApp() {
  const { accessToken } = useParams();
  return (
    <CaptureProvider accessToken={accessToken}>
      <CaptureRoutes />
    </CaptureProvider>
  );
}
