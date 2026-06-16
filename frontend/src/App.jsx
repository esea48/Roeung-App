import { Route, Routes } from 'react-router-dom';
import CaptureApp from './pages/capture/CaptureApp';
import BookApp from './pages/book/BookApp';
import KeeperApp from './pages/keeper/KeeperApp';

function App() {
  return (
    <Routes>
      <Route path="/f/:accessToken/capture/*" element={<CaptureApp />} />
      <Route path="/f/:accessToken/book/*" element={<BookApp />} />
      <Route path="/keeper/*" element={<KeeperApp />} />
      <Route path="*" element={<p>Roeung — open your family link to continue.</p>} />
    </Routes>
  );
}

export default App;
