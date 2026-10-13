#ifndef cms_lpc_llp_MCLongLivedParticles_h
#define cms_lpc_llp_MCLongLivedParticles_h
// -*- C++ -*-
//
// Package:    cms_lpc_llp/llp_ntupler
// Class:      MCLongLivedParticles
//
/*
 Description: keep only events in which a long-lived particle decays inside the
              muon system acceptance (CSC or DT), or slightly before it
              (calorimeters / solenoid), so that the decay products can still
              produce a muon detector shower.

 Implementation: the decay vertex is taken from the HepMC record
                 (generatorSmeared), i.e. it is the *generator* decay point,
                 before Geant4. Positions in the HepMC record are in mm; all
                 configuration parameters below are in cm and converted
                 internally.

 Original Author:  Filip Moortgat (GeneratorInterface/GenFilters)
 Adapted for the LLP muon-system analysis.
*/

#include <vector>

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/global/EDFilter.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "FWCore/Utilities/interface/StreamID.h"

#include "SimDataFormats/GeneratorProducts/interface/HepMCProduct.h"

class MCLongLivedParticles : public edm::global::EDFilter<> {
public:
  explicit MCLongLivedParticles(const edm::ParameterSet&);
  ~MCLongLivedParticles() override = default;

  static void fillDescriptions(edm::ConfigurationDescriptions&);

  bool filter(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

private:
  // true if (r, z) [cm] is inside the accepted decay volume
  bool inAcceptance(double r, double z) const;

  const edm::EDGetTokenT<edm::HepMCProduct> token_;

  const std::vector<int> particleIDs_;  // |pdgId| of the long-lived particles
  const int nRequired_;                 // how many of them must decay in the volume
  const double maxAbsEta_;              // eta cut on the LLP momentum

  // Accepted decay volume, in cm: inside the outer envelope but outside the
  // inner cylinder (tracker + ECAL), i.e. muon system "and a bit before".
  const double innerVetoR_;
  const double innerVetoZ_;
  const double maxR_;
  const double maxZ_;

  const bool verbose_;
};
#endif
