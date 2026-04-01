import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ChunksPage } from './pages/ChunksPage'
import { UploadPage } from './pages/UploadPage'
import { ChatPage } from './pages/ChatPage'
import { IngredientsPage } from './pages/IngredientsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/chunks" replace />} />
          <Route path="chunks" element={<ChunksPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="ingredients" element={<IngredientsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
