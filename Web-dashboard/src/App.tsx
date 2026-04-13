import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import HITLInbox from './pages/HITLInbox'
import Inventory from './pages/Inventory'

function App() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/hitl" element={<HITLInbox />} />
        <Route path="/inventory" element={<Inventory />} />
      </Routes>
    </AnimatePresence>
  )
}

export default App
