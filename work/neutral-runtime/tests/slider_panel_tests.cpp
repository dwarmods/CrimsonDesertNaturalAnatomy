#include "slider_panel.h"
#include <cstdio>
#include <stdexcept>
using namespace neutral;
static void require(bool good,const char* why) {if (!good) throw std::runtime_error(why);}
int main() {try {
    FitMesh m;m.base={{0,0,0},{0,0,-.1}};m.seam_normals.assign(2,{0,1,0});
    for (auto& f:m.fields) f.assign(2,0);m.fields[FitMesh::AnatomyHeight][1]=1;
    ControlSession session(std::make_shared<const Fitter>(std::move(m)));
    ImGui::CreateContext();auto& io=ImGui::GetIO();io.IniFilename=nullptr;
    io.DisplaySize={1280,1000};io.DeltaTime=1.f/60;
    unsigned char* pixels;int w,h;io.Fonts->GetTexDataAsRGBA32(&pixels,&w,&h);
    SliderPanel panel;
    auto frame=[&](PanelMode mode=PanelMode::OfflinePreview) {
        ImGui::NewFrame();ImGui::SetNextWindowPos({10,10},ImGuiCond_Always);panel.draw(session,mode);ImGui::Render();
    };
    for (int i=0;i<3;++i) frame();
    auto click=[&](PanelRect r,float fraction=0.5f,PanelMode mode=PanelMode::OfflinePreview) {
        io.AddMousePosEvent(r.minimum.x+(r.maximum.x-r.minimum.x)*fraction,(r.minimum.y+r.maximum.y)*.5f);frame(mode);
        io.AddMouseButtonEvent(0,true);frame(mode);io.AddMouseButtonEvent(0,false);frame(mode);frame(mode);
    };
    click(panel.control_rects()[0],.8f);const auto moved=session.snapshot().requested;
    require(moved[0]>10,"mouse slider did not reach control worker");
    click(panel.undo_rect());require(session.snapshot().requested==default_parameters(),"Undo failed after slider gesture");
    auto preset=default_parameters();preset[6]=1.2;
    require(panel.apply_preset(session,preset),"preset import failed");frame();
    click(panel.reset_rect());require(session.snapshot().requested==default_parameters(),"Reset all failed");
    click(panel.undo_rect());require(session.snapshot().requested==preset,"reset was not undoable");
    // External writes invalidate the panel's undo history.
    auto s=session.snapshot();auto other=s.requested;other[0]=-10;session.edit(s.requested_revision,other);frame();
    click(panel.undo_rect());require(session.snapshot().requested==other,"Undo overwrote an external edit");
    auto rect=panel.control_rects()[0];
    io.AddMousePosEvent(rect.minimum.x+(rect.maximum.x-rect.minimum.x)*.7f,(rect.minimum.y+rect.maximum.y)*.5f);frame();
    io.AddMouseButtonEvent(0,true);frame();
    s=session.snapshot();auto during_drag=s.requested;during_drag[6]=.9;session.edit(s.requested_revision,during_drag);frame();
    io.AddMouseButtonEvent(0,false);frame();frame();const auto after_drag=session.snapshot().requested;
    click(panel.undo_rect());require(session.snapshot().requested==after_drag && after_drag[6]==.9,"gesture undo overwrote a concurrent edit");
    other=session.snapshot().requested;
    frame(PanelMode::AwaitingBinding);click(panel.control_rects()[0],.2f,PanelMode::AwaitingBinding);
    require(session.snapshot().requested==other,"unbound in-game controls were editable");
    require(panel.take_preset_action()==PresetAction::None,"unexpected file action");
    ImGui::DestroyContext();std::puts("PASS: actual ImGui mouse edits, undo, reset, external-change protection and unbound-control gating.");return 0;
}catch(const std::exception& e) {std::fprintf(stderr,"FAIL: %s\n",e.what());if(ImGui::GetCurrentContext()) ImGui::DestroyContext();return 1;}}
