#include "control_session.h"
#include <cstdio>
#include <stdexcept>
using namespace neutral;
static void require(bool p,const char* message) {if (!p) throw std::runtime_error(message);}
int main() {try {
    FitMesh m;m.base={{0,0,0},{0,0,-.1}};m.seam_normals.assign(2,{0,1,0});
    for (auto& f:m.fields) f.assign(2,0);
    m.fields[FitMesh::Shaft][1]=1;
    auto fitter=std::make_shared<const Fitter>(std::move(m));
    ControlSession session(fitter);auto s=session.snapshot();
    require(session.wait_for_staged(1,std::chrono::seconds(2)),"initial solve timed out");
    auto stable=session.snapshot().staged_positions;
    auto p=s.requested;p[static_cast<unsigned>(Control::Length)]=1.2;
    require(session.edit(s.requested_revision,p)==EditResult::Accepted,"edit refused");
    require(session.edit(s.requested_revision,p)==EditResult::Stale,"stale edit accepted");
    auto next=session.snapshot();require(session.edit(next.requested_revision,p)==EditResult::Unchanged,"unchanged edit rebuilds");
    p[0]=100;require(session.edit(next.requested_revision,p)==EditResult::Invalid,"invalid edit accepted");
    require(session.snapshot().requested_revision==next.requested_revision,"invalid edit changed state");
    for (unsigned i=0;i<200;++i) {
        s=session.snapshot();p=s.requested;p[static_cast<unsigned>(Control::Length)]=.75+.6*i/199.;
        require(session.edit(s.requested_revision,p)==EditResult::Accepted,"drag edit refused");
    }
    s=session.snapshot();require(session.wait_for_staged(s.requested_revision,std::chrono::seconds(2)),"latest drag did not finish");
    next=session.snapshot();require(next.staged_revision==next.requested_revision,"wrong staged revision");
    require(std::abs(next.staged_positions->at(1).z+.135)<1e-12,"wrong staged deformation");
    require(stable->at(1).z==-.1,"published snapshot was mutated");
    require(next.error.empty(),"unexpected solve error");
    std::puts("PASS: revision guards, rejected-edit isolation, 200 coalesced drag updates, immutable output snapshots and worker completion.");
    return 0;
} catch(const std::exception& e) {std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
