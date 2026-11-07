#pragma once
#include "control_session.h"
#include <imgui.h>
#include <deque>
namespace neutral {
enum class PresetAction { None, Load, Save };
enum class PanelMode { OfflinePreview, AwaitingBinding };
struct PanelRect {ImVec2 minimum{},maximum{};};
class SliderPanel {
public:
    void draw(ControlSession& session, PanelMode mode=PanelMode::OfflinePreview);
    bool apply_preset(ControlSession& session,const Parameters& parameters);
    PresetAction take_preset_action();
    const std::array<PanelRect,control_count>& control_rects() const {return rectangles_;}
    PanelRect undo_rect() const {return undo_rect_;}
    PanelRect reset_rect() const {return reset_rect_;}
    void set_notice(std::string text) {notice_=std::move(text);}
private:
    void remember(const Parameters& parameters);
    bool undo(ControlSession& session);
    Parameters editing_{},gesture_before_{};
    std::uint64_t known_revision_{};
    bool gesture_valid_{};
    std::deque<Parameters> undo_;
    std::array<PanelRect,control_count> rectangles_{};
    PanelRect undo_rect_{},reset_rect_{};
    PresetAction action_{PresetAction::None};
    std::string notice_;
};
}
