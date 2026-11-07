#include "control_session.h"
#include <stdexcept>

namespace neutral {
ControlSession::ControlSession(std::shared_ptr<const Fitter> fitter,Parameters initial):fitter_(std::move(fitter)) {
    if (!fitter_ || !valid_parameters(initial)) throw std::invalid_argument("invalid fitting session");
    state_.requested=initial;state_.requested_revision=1;
    worker_=std::thread([this]{run();});
}
ControlSession::~ControlSession() {
    {std::lock_guard<std::mutex> lock(mutex_);stop_=true;}
    changed_.notify_all();if (worker_.joinable()) worker_.join();
}
ControlSnapshot ControlSession::snapshot() const {std::lock_guard<std::mutex> lock(mutex_);return state_;}
EditResult ControlSession::edit(std::uint64_t expected_revision,const Parameters& parameters) {
    if (!valid_parameters(parameters)) return EditResult::Invalid;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (expected_revision!=state_.requested_revision) return EditResult::Stale;
        if (parameters==state_.requested) return EditResult::Unchanged;
        state_.requested=parameters;++state_.requested_revision;state_.error.clear();
    }
    changed_.notify_all();return EditResult::Accepted;
}
bool ControlSession::wait_for_staged(std::uint64_t revision,std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock(mutex_);
    changed_.wait_for(lock,timeout,[&]{return stop_ || state_.staged_revision>=revision || !state_.error.empty();});
    return state_.staged_revision>=revision;
}
void ControlSession::run() {
    std::unique_lock<std::mutex> lock(mutex_);
    std::uint64_t attempted=0;
    while (!stop_) {
        changed_.wait(lock,[&]{return stop_ || state_.requested_revision!=attempted;});
        if (stop_) break;
        // Coalesce dragging; heavy mesh work never runs on the caller/render thread.
        auto revision=state_.requested_revision;
        while (changed_.wait_for(lock,std::chrono::milliseconds(50),[&]{return stop_ || state_.requested_revision!=revision;})) {
            if (stop_) return;
            revision=state_.requested_revision;
        }
        const auto parameters=state_.requested;attempted=revision;
        lock.unlock();
        std::shared_ptr<const std::vector<Vec3>> result;std::string error;
        try {result=std::make_shared<const std::vector<Vec3>>(fitter_->deform(parameters));}
        catch (const std::exception& e) {error=e.what();}
        catch (...) {error="unknown fitting failure";}
        lock.lock();
        // A superseded solve must never overwrite newer settings or geometry.
        if (!stop_ && state_.requested_revision==revision) {
            if (result) {state_.staged_positions=std::move(result);state_.staged_revision=revision;}
            state_.error=std::move(error);changed_.notify_all();
        }
    }
}
}
