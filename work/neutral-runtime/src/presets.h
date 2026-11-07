#pragma once
#include "fitting.h"
#include <string_view>
namespace neutral {
std::string preset_json(const Parameters& parameters);
Parameters parse_preset(std::string_view text);
Parameters load_preset(const std::filesystem::path& path);
// Same-directory exclusive temporary file, flushed before atomic replacement.
void save_preset_atomic(const std::filesystem::path& path, const Parameters& parameters);
}
