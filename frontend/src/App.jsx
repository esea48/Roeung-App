import { Route, Routes } from 'react-router-dom';
import CaptureApp from './pages/capture/CaptureApp';

function App() {
  return (
    <Routes>
      <Route path="/f/:accessToken/capture/*" element={<CaptureApp />} />
      <Route path="*" element={<p>Roeung — open your family link to continue.</p>} />
    </Routes>
  );
}

export default App;
