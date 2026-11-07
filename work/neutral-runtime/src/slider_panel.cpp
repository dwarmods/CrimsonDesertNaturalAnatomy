#include "slider_panel.h"
#include <algorithm>
namespace neutral {
static PanelRect last_rect() {return {ImGui::GetItemRectMin(),ImGui::GetItemRectMax()};}
void SliderPanel::remember(const Parameters& p) {
    if (undo_.empty() || undo_.back()!=p) undo_.push_back(p);
    if (undo_.size()>32) undo_.pop_front();
}
bool SliderPanel::apply_preset(ControlSession& session,const Parameters& p) {
    const auto state=session.snapshot();const auto result=session.edit(state.requested_revision,p);
    if (result==EditResult::Invalid || result==EditResult::Stale) return false;
    if (result==EditResult::Accepted) remember(state.requested);
    const auto now=session.snapshot();editing_=now.requested;known_revision_=now.requested_revision;
    return true;
}
bool SliderPanel::undo(ControlSession& session) {
    if (undo_.empty()) return false;
    const auto state=session.snapshot();const auto p=undo_.back();
    if (state.requested_revision!=known_revision_) {undo_.clear();gesture_valid_=false;return false;}
    const auto result=session.edit(state.requested_revision,p);
    if (result==EditResult::Invalid || result==EditResult::Stale) return false;
    undo_.pop_back();const auto now=session.snapshot();editing_=now.requested;known_revision_=now.requested_revision;
    return true;
}
PresetAction SliderPanel::take_preset_action() {const auto action=action_;action_=PresetAction::None;return action;}
void SliderPanel::draw(ControlSession& session,PanelMode mode) {
    const auto state=session.snapshot();
    if (known_revision_!=state.requested_revision) {
        // Another editor changed this session: do not undo over its newer settings.
        if (known_revision_) undo_.clear();
        gesture_valid_=false;
        editing_=state.requested;known_revision_=state.requested_revision;
    }
    ImGui::SetNextWindowSize({752,912},ImGuiCond_FirstUseEver);
    if (!ImGui::Begin("Natural Anatomy")) {ImGui::End();return;}
    ImGui::TextUnformatted(mode==PanelMode::OfflinePreview?"Offline fitting preview":"Waiting for verified game binding");
    ImGui::TextWrapped("Visible game body updates are not connected in this build.");
    ImGui::Separator();
    ImGui::Text("Requested: %llu   CPU ready: %llu",state.requested_revision,state.staged_revision);
    if (state.staged_revision<state.requested_revision) ImGui::TextUnformatted("Preparing geometry...");
    if (!state.error.empty()) ImGui::TextWrapped("Fitting error: %s",state.error.c_str());
    if (!notice_.empty()) ImGui::TextWrapped("%s",notice_.c_str());
    const bool enabled=mode==PanelMode::OfflinePreview;
    ImGui::BeginDisabled(!enabled);
    bool changed=false,finished=false;
    static constexpr unsigned order[]{0,10,14,15,6,3,4,5,7,8,9,1,2,11,12,13};
    for (unsigned at_index=0;at_index<control_count;++at_index) {
        if (at_index==0) ImGui::SeparatorText("Position");
        if (at_index==4) ImGui::SeparatorText("Shaft");
        if (at_index==8) ImGui::SeparatorText("Testicles");
        if (at_index==11) ImGui::SeparatorText("Attachment");
        if (at_index==13) ImGui::SeparatorText("Overall size");
        const unsigned i=order[at_index];
        const auto& spec=control_specs()[i];ImGui::PushID(spec.key);
        const float width=std::max(130.f,ImGui::GetContentRegionAvail().x-215.f);
        ImGui::SetNextItemWidth(width);
        const char* format=(i==0 || i==1 || i==8 || i==9 || i==10 || i==14 || i==15)?"%.1f mm":i==2?"%.2f":"%.3fx";
        const bool edited=ImGui::SliderScalar(spec.label,ImGuiDataType_Double,&editing_[i],&spec.minimum,&spec.maximum,format,ImGuiSliderFlags_AlwaysClamp);
        const auto at=ImGui::GetItemRectMin();rectangles_[i]={at,{at.x+width,at.y+ImGui::GetFrameHeight()}};
        if (ImGui::IsItemActivated()) {gesture_before_=state.requested;gesture_valid_=true;}
        changed|=edited;finished|=ImGui::IsItemDeactivatedAfterEdit();
        ImGui::PopID();
    }
    if (changed) {
        const auto result=session.edit(state.requested_revision,editing_);
        if (result==EditResult::Accepted || result==EditResult::Unchanged) known_revision_=session.snapshot().requested_revision;
        else {editing_=session.snapshot().requested;gesture_valid_=false;notice_="Edit was rejected; controls were refreshed.";}
    }
    if (finished) {if (gesture_valid_ && editing_!=gesture_before_) remember(gesture_before_);gesture_valid_=false;}
    ImGui::Separator();
    ImGui::BeginDisabled(undo_.empty());
    if (ImGui::Button("Undo")) undo(session);undo_rect_=last_rect();
    ImGui::EndDisabled();ImGui::SameLine();
    if (ImGui::Button("Reset all")) apply_preset(session,default_parameters());reset_rect_=last_rect();
    ImGui::SameLine();if (ImGui::Button("Load preset")) action_=PresetAction::Load;
    ImGui::SameLine();if (ImGui::Button("Save preset")) action_=PresetAction::Save;
    ImGui::EndDisabled();
    ImGui::TextWrapped("Length and width are relative multipliers. Position, hang, separation and contour use millimetres.");
    ImGui::End();
}
}
