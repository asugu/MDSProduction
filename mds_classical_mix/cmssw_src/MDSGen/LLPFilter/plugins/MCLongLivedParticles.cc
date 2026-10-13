#include "MDSGen/LLPFilter/interface/MCLongLivedParticles.h"

#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include <algorithm>
#include <cmath>

namespace {
  // HepMC stores lengths in mm, the rest of CMSSW works in cm
  constexpr double kMMtoCM = 0.1;

  // A generator record contains "carbon copies": the same particle repeated
  // with an intermediate vertex. Those are not real decays, skip them.
  bool isCarbonCopy(const HepMC::GenParticle* p) {
    const HepMC::GenVertex* end = p->end_vertex();
    if (end == nullptr)
      return false;
    for (auto child = end->particles_out_const_begin(); child != end->particles_out_const_end(); ++child) {
      if ((*child)->pdg_id() == p->pdg_id())
        return true;
    }
    return false;
  }
}  // namespace

MCLongLivedParticles::MCLongLivedParticles(const edm::ParameterSet& iConfig)
    : token_(consumes<edm::HepMCProduct>(iConfig.getParameter<edm::InputTag>("hepMCProductTag"))),
      particleIDs_(iConfig.getParameter<std::vector<int>>("particleIDs")),
      nRequired_(iConfig.getParameter<int>("nRequired")),
      maxAbsEta_(iConfig.getParameter<double>("maxAbsEta")),
      innerVetoR_(iConfig.getParameter<double>("innerVetoR")),
      innerVetoZ_(iConfig.getParameter<double>("innerVetoZ")),
      maxR_(iConfig.getParameter<double>("maxR")),
      maxZ_(iConfig.getParameter<double>("maxZ")),
      verbose_(iConfig.getUntrackedParameter<bool>("verbose")) {}

void MCLongLivedParticles::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("hepMCProductTag", edm::InputTag("generatorSmeared"));
  desc.add<std::vector<int>>("particleIDs", {9900015});
  desc.add<int>("nRequired", 1);
  desc.add<double>("maxAbsEta", 4.0);
  // defaults: decay outside the tracker+ECAL cylinder, inside the muon system envelope
  desc.add<double>("innerVetoR", 200.0);
  desc.add<double>("innerVetoZ", 400.0);
  desc.add<double>("maxR", 800.0);
  desc.add<double>("maxZ", 1200.0);
  desc.addUntracked<bool>("verbose", false);
  descriptions.add("MCLongLivedParticles", desc);
}

bool MCLongLivedParticles::inAcceptance(double r, double z) const {
  const double absZ = std::fabs(z);
  // must be past the tracker/ECAL barrel+endcap cylinder ...
  if (absZ < innerVetoZ_ && r < innerVetoR_)
    return false;
  // ... and still inside CMS
  return (absZ < maxZ_ && r < maxR_);
}

bool MCLongLivedParticles::filter(edm::StreamID, edm::Event& iEvent, const edm::EventSetup&) const {
  const edm::Handle<edm::HepMCProduct>& evt = iEvent.getHandle(token_);

  const HepMC::GenEvent* generated_event = evt->GetEvent();

  int nFound = 0;
  for (auto p = generated_event->particles_begin(); p != generated_event->particles_end(); ++p) {
    const int pdgId = std::abs((*p)->pdg_id());
    if (std::find(particleIDs_.begin(), particleIDs_.end(), pdgId) == particleIDs_.end())
      continue;

    const HepMC::GenVertex* end = (*p)->end_vertex();
    if (end == nullptr) {
      if (verbose_)
        edm::LogPrint("MCLongLivedParticles") << "LLP " << pdgId << " has no end vertex (stable in the generator)";
      continue;
    }
    if (isCarbonCopy(*p))
      continue;

    const double x = end->position().x() * kMMtoCM;
    const double y = end->position().y() * kMMtoCM;
    const double z = end->position().z() * kMMtoCM;
    const double r = std::sqrt(x * x + y * y);
    const double eta = (*p)->momentum().eta();

    const bool accepted = inAcceptance(r, z) && std::fabs(eta) < maxAbsEta_;
    if (verbose_) {
      edm::LogPrint("MCLongLivedParticles")
          << "LLP " << pdgId << " decay at r = " << r << " cm, z = " << z << " cm, eta = " << eta
          << " -> " << (accepted ? "accepted" : "rejected");
    }
    if (accepted)
      ++nFound;
  }

  const bool pass = (nFound >= nRequired_);
  if (verbose_)
    edm::LogPrint("MCLongLivedParticles") << "found " << nFound << " LLP decays in acceptance, event "
                                          << (pass ? "passes" : "fails");
  return pass;
}

DEFINE_FWK_MODULE(MCLongLivedParticles);
