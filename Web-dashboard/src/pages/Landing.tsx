import { motion } from 'framer-motion'
import LandingNav from '../components/landing/LandingNav'
import HeroSection from '../components/landing/HeroSection'
import ContourSection from '../components/landing/ContourSection'
import FeaturesRow from '../components/landing/FeaturesRow'
import StatsTicker from '../components/landing/StatsTicker'
import HowItWorks from '../components/landing/HowItWorks'
import HITLTeaser from '../components/landing/HITLTeaser'
import FinalCTA from '../components/landing/FinalCTA'
import Footer from '../components/landing/Footer'

export default function Landing() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      <LandingNav />
      <HeroSection />
      <ContourSection />
      <FeaturesRow />
      <StatsTicker />
      <HowItWorks />
      <HITLTeaser />
      <FinalCTA />
      <Footer />
    </motion.div>
  )
}
