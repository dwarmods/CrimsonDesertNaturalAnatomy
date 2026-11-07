#include "motion.h"
#include <cstdio>
#include <stdexcept>
#include <algorithm>
using namespace neutral;
void require(bool p,const char* reason){if(!p)throw std::runtime_error(reason);}
std::vector<Node> nodes(){return {{{0,0,0},-1,.005,true},{{0,-.05,.012},0,.006,false},{{0,-.1,.02},1,.006,false},{{-.018,-.05,-.016},0,.009,false},{{.018,-.05,-.016},0,.009,false}};}
void valid(const Motion& m){for(auto p:m.positions())require(finite(p),"finite state");require(m.worst_length_error()<.001,"segment length preservation");}
int main(){try{
 Frame root{};Motion a(nodes()),b(nodes());
 for(int i=0;i<600;++i)a.update(1./60,root,Visibility::Nude);
 for(int i=0;i<1200;++i)b.update(1./120,root,Visibility::Nude);
 valid(a);valid(b);double rate_error=0;for(size_t i=0;i<a.positions().size();++i)rate_error=std::max(rate_error,length(a.positions()[i]-b.positions()[i]));require(rate_error<1e-8,"render rate independence at rest");
 for(int i=0;i<2400;++i){double t=i/120.;root.position={.025*std::sin(4*t),.015*std::sin(6*t),.01*std::sin(3*t)};a.update(1./120,root,Visibility::Nude);valid(a);require(length(a.positions()[0]-root.position)<1e-9,"fixed root anchoring");}
 a.update(1./60,root,Visibility::Clothed);require(!a.active(),"clothed passthrough");auto rest=a.rest_positions(root);for(size_t i=0;i<rest.size();++i)require(length(rest[i]-a.positions()[i])<1e-12,"clothed baseline");
 a.update(1./60,root,Visibility::Unknown);require(!a.active(),"unknown visibility disables simulation");
 root.position={200,20,-100};a.update(1./60,root,Visibility::Nude);require(!a.active(),"teleport resets");
 a.update(1.,root,Visibility::Nude);require(!a.active(),"long frame resets");
 Motion c({{{0,0,0},-1,.001,true},{{.04,-.03,0},0,.005,false}});Frame f{};std::vector<Capsule> capsules{{{-.1,-.04,0},{.1,-.04,0},.01}};
 for(int i=0;i<600;++i)c.update(1./120,f,Visibility::Nude,capsules);
 require(length(c.positions()[1]-Vec3{c.positions()[1].x,-.04,0})>=.015-1e-6,"capsule exclusion");valid(c);
 bool rejected=false;try{Motion bad({{{},-1,.01,false}});}catch(const std::invalid_argument&){rejected=true;}require(rejected,"invalid chain rejected");
 std::printf("PASS: fixed roots, segment constraints, frame-rate parity, motion stability, clothing gating, teleport/long-frame resets, capsule collision, invalid input rejection. Rest-rate max error %.9g m\n",rate_error);return 0;
 }catch(const std::exception& e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
