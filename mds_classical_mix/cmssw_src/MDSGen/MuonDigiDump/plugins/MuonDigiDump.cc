// Flat dump of muon digis, one tree entry per digi, for sim vs unpacked (from RAW) comparison.
#include "FWCore/Framework/interface/one/EDAnalyzer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "CommonTools/UtilAlgos/interface/TFileService.h"
#include "DataFormats/CSCDigi/interface/CSCStripDigiCollection.h"
#include "DataFormats/CSCDigi/interface/CSCWireDigiCollection.h"
#include "DataFormats/CSCDigi/interface/CSCComparatorDigiCollection.h"
#include "DataFormats/DTDigi/interface/DTDigiCollection.h"
#include "DataFormats/RPCDigi/interface/RPCDigiCollection.h"
#include "DataFormats/GEMDigi/interface/GEMDigiCollection.h"
#include "SimDataFormats/TrackingHit/interface/PSimHit.h"
#include "SimDataFormats/CrossingFrame/interface/CrossingFrame.h"
#include "SimDataFormats/CrossingFrame/interface/PCrossingFrame.h"
#include "SimDataFormats/CrossingFrame/interface/MixCollection.h"
#include "TTree.h"
#include <algorithm>
#include <string>
#include <vector>

class MuonDigiDump : public edm::one::EDAnalyzer<edm::one::SharedResources> {
public:
  explicit MuonDigiDump(const edm::ParameterSet&);
  void analyze(const edm::Event&, const edm::EventSetup&) override;

private:
  // src index 0 = sim, 1 = unpacked
  std::vector<edm::EDGetTokenT<CSCStripDigiCollection>> strip_;
  std::vector<edm::EDGetTokenT<CSCWireDigiCollection>> wire_;
  std::vector<edm::EDGetTokenT<CSCComparatorDigiCollection>> comp_;
  std::vector<edm::EDGetTokenT<DTDigiCollection>> dt_;
  std::vector<edm::EDGetTokenT<RPCDigiCollection>> rpc_;
  std::vector<edm::EDGetTokenT<GEMDigiCollection>> gem_;
  edm::EDGetTokenT<PCrossingFrame<PSimHit>> cscXF_;

  TTree *tSim_, *tStrip_, *tWire_, *tComp_, *tDT_, *tRPC_, *tGEM_;
  // id[0..5] = detector-specific DetId fields (see branch titles)
  int ev_, src_, id_[6], ch_, adc_[8], nAdc_, tbin_, nTbOn_, val_, cnt_;
  float tof_, eloss_;
};

MuonDigiDump::MuonDigiDump(const edm::ParameterSet& p) {
  usesResource("TFileService");
  for (const auto& l : {p.getParameter<std::string>("simCSC"), p.getParameter<std::string>("rawCSC")}) {
    strip_.push_back(consumes<CSCStripDigiCollection>(edm::InputTag(l, "MuonCSCStripDigi")));
    wire_.push_back(consumes<CSCWireDigiCollection>(edm::InputTag(l, "MuonCSCWireDigi")));
    comp_.push_back(consumes<CSCComparatorDigiCollection>(edm::InputTag(l, "MuonCSCComparatorDigi")));
  }
  for (const auto& t : p.getParameter<std::vector<edm::InputTag>>("dt"))
    dt_.push_back(consumes<DTDigiCollection>(t));
  for (const auto& t : p.getParameter<std::vector<edm::InputTag>>("rpc"))
    rpc_.push_back(consumes<RPCDigiCollection>(t));
  for (const auto& t : p.getParameter<std::vector<edm::InputTag>>("gem"))
    gem_.push_back(consumes<GEMDigiCollection>(t));

  cscXF_ = consumes<PCrossingFrame<PSimHit>>(edm::InputTag("mix", "g4SimHitsMuonCSCHits"));

  edm::Service<TFileService> fs;
  auto book = [&](const char* name, const char* idTitle) {
    TTree* t = fs->make<TTree>(name, idTitle);
    t->Branch("ev", &ev_);
    t->Branch("src", &src_);
    t->Branch("id", id_, "id[6]/I");
    t->Branch("ch", &ch_);
    return t;
  };
  // CSC SimHits from the crossing frame: src = origin (0 signal, 1 in-time PU, 2 OOT PU), val = BX, cnt = pdgId
  tSim_ = book("cscsim", "id=endcap,station,ring,chamber,layer,0; ch=strip of entry point");
  tSim_->Branch("bx", &val_);
  tSim_->Branch("pdg", &cnt_);
  tSim_->Branch("tof", &tof_);
  tSim_->Branch("eloss", &eloss_);
  tStrip_ = book("strip", "id=endcap,station,ring,chamber,layer,0; ch=strip");
  tStrip_->Branch("nAdc", &nAdc_);
  tStrip_->Branch("adc", adc_, "adc[8]/I");
  tWire_ = book("wire", "id=endcap,station,ring,chamber,layer,0; ch=wiregroup");
  tWire_->Branch("tbin", &tbin_);
  tWire_->Branch("nTbOn", &nTbOn_);
  tComp_ = book("comp", "id=endcap,station,ring,chamber,layer,0; ch=strip");
  tComp_->Branch("tbin", &tbin_);
  tComp_->Branch("val", &val_);
  tDT_ = book("dt", "id=wheel,station,sector,superlayer,layer,0; ch=wire");
  tDT_->Branch("tdc", &val_);
  tDT_->Branch("number", &cnt_);
  tRPC_ = book("rpc", "id=region,ring,station,sector,layer,subsector*10+roll; ch=strip");
  tRPC_->Branch("bx", &val_);
  tGEM_ = book("gem", "id=region,ring,station,layer,chamber,roll; ch=strip");
  tGEM_->Branch("bx", &val_);
}

void MuonDigiDump::analyze(const edm::Event& e, const edm::EventSetup&) {
  ev_ = e.id().event();
  auto cscId = [&](const CSCDetId& d) {
    int v[6] = {d.endcap(), d.station(), d.ring(), d.chamber(), d.layer(), 0};
    std::copy(v, v + 6, id_);
  };
  edm::Handle<PCrossingFrame<PSimHit>> hx;
  if (e.getByToken(cscXF_, hx)) {
    // PCrossingFrame can't be iterated: rebuild a CrossingFrame as in the ntupler
    const PCrossingFrame<PSimHit>& pcf = *hx;
    CrossingFrame<PSimHit> cf;
    cf.setBunchRange(pcf.getBunchRange());
    cf.setBunchSpace(pcf.getBunchSpace());
    cf.setMaxNbSources(pcf.getMaxNbSources());
    cf.setSubDet(pcf.getSubDet());
    cf.setPileupOffsetsBcr(pcf.getPileupOffsetsBcr());
    cf.setPileupOffsetsSource(pcf.getPileupOffsetsSource());
    cf.addSignals(&pcf.getSignals(), pcf.getEventID());
    cf.setPileups(pcf.getPileups());
    MixCollection<PSimHit> col(&cf);
    for (MixCollection<PSimHit>::MixItr it = col.begin(); it != col.end(); ++it) {
      cscId(CSCDetId(it->detUnitId()));
      val_ = it.bunch();
      src_ = it.getTrigger() ? 0 : (val_ == 0 ? 1 : 2);
      ch_ = -1;
      cnt_ = it->particleType();
      tof_ = it->timeOfFlight();
      eloss_ = it->energyLoss();
      tSim_->Fill();
    }
  }
  for (src_ = 0; src_ < 2; ++src_) {
    edm::Handle<CSCStripDigiCollection> hs;
    if (e.getByToken(strip_[src_], hs))
      for (auto it = hs->begin(); it != hs->end(); ++it) {
        cscId((*it).first);
        for (auto d = (*it).second.first; d != (*it).second.second; ++d) {
          ch_ = d->getStrip();
          const auto& a = d->getADCCounts();
          nAdc_ = a.size();
          for (int i = 0; i < 8; ++i)
            adc_[i] = i < nAdc_ ? a[i] : -1;
          tStrip_->Fill();
        }
      }
    edm::Handle<CSCWireDigiCollection> hw;
    if (e.getByToken(wire_[src_], hw))
      for (auto it = hw->begin(); it != hw->end(); ++it) {
        cscId((*it).first);
        for (auto d = (*it).second.first; d != (*it).second.second; ++d) {
          ch_ = d->getWireGroup();
          tbin_ = d->getTimeBin();
          nTbOn_ = d->getTimeBinsOn().size();
          tWire_->Fill();
        }
      }
    edm::Handle<CSCComparatorDigiCollection> hc;
    if (e.getByToken(comp_[src_], hc))
      for (auto it = hc->begin(); it != hc->end(); ++it) {
        cscId((*it).first);
        for (auto d = (*it).second.first; d != (*it).second.second; ++d) {
          ch_ = d->getStrip();
          tbin_ = d->getTimeBin();
          val_ = d->getComparator();
          tComp_->Fill();
        }
      }
    if (src_ < (int)dt_.size()) {
      edm::Handle<DTDigiCollection> h;
      if (e.getByToken(dt_[src_], h))
        for (auto it = h->begin(); it != h->end(); ++it) {
          const DTLayerId& d = (*it).first;
          int v[6] = {d.wheel(), d.station(), d.sector(), d.superlayer(), d.layer(), 0};
          std::copy(v, v + 6, id_);
          for (auto g = (*it).second.first; g != (*it).second.second; ++g) {
            ch_ = g->wire();
            val_ = g->countsTDC();
            cnt_ = g->number();
            tDT_->Fill();
          }
        }
    }
    if (src_ < (int)rpc_.size()) {
      edm::Handle<RPCDigiCollection> h;
      if (e.getByToken(rpc_[src_], h))
        for (auto it = h->begin(); it != h->end(); ++it) {
          const RPCDetId& d = (*it).first;
          int v[6] = {d.region(), d.ring(), d.station(), d.sector(), d.layer(), d.subsector() * 10 + d.roll()};
          std::copy(v, v + 6, id_);
          for (auto g = (*it).second.first; g != (*it).second.second; ++g) {
            ch_ = g->strip();
            val_ = g->bx();
            tRPC_->Fill();
          }
        }
    }
    if (src_ < (int)gem_.size()) {
      edm::Handle<GEMDigiCollection> h;
      if (e.getByToken(gem_[src_], h))
        for (auto it = h->begin(); it != h->end(); ++it) {
          const GEMDetId& d = (*it).first;
          int v[6] = {d.region(), d.ring(), d.station(), d.layer(), d.chamber(), d.roll()};
          std::copy(v, v + 6, id_);
          for (auto g = (*it).second.first; g != (*it).second.second; ++g) {
            ch_ = g->strip();
            val_ = g->bx();
            tGEM_->Fill();
          }
        }
    }
  }
}

DEFINE_FWK_MODULE(MuonDigiDump);
