#pragma once
#include "fitting.h"
#include <chrono>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <thread>

namespace neutral {
struct ControlSnapshot {
    Parameters requested{};
    std::uint64_t requested_revision{}, staged_revision{};
    std::shared_ptr<const std::vector<Vec3>> staged_positions;
    std::string error;
    // Staged means CPU geometry only. No game renderer has acknowledged it.
};
enum class EditResult { Accepted, Unchanged, Invalid, Stale };
class ControlSession {
public:
    explicit ControlSession(std::shared_ptr<const Fitter> fitter, Parameters initial=default_parameters());
    ~ControlSession();
    ControlSession(const ControlSession&)=delete;
    ControlSession& operator=(const ControlSession&)=delete;
    ControlSnapshot snapshot() const;
    EditResult edit(std::uint64_t expected_revision, const Parameters& parameters);
    bool wait_for_staged(std::uint64_t revision, std::chrono::milliseconds timeout);
private:
    void run();
    std::shared_ptr<const Fitter> fitter_;
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    ControlSnapshot state_;
    bool stop_{};
    std::thread worker_;
};
}
