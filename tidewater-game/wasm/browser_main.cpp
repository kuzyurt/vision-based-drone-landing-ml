// Browser entry points; the linked flight modules remain the pinned PX4 code.
#include <emscripten/emscripten.h>
#include <px4_platform_common/init.h>
#include <px4_platform_common/tasks.h>
#include <pthread.h>
#include <unistd.h>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <cstring>
#include <thread>
#include <atomic>
#include <climits>
#include "apps.h"

extern pthread_t _shell_task_id;
namespace px4 { void init_once(); }
static apps_map_type applications;
static std::map<pthread_t, std::string> thread_names;
static std::mutex names_mutex;

// Emscripten has pthreads but no host thread naming calls. PX4 also reads these
// names in diagnostics, so retain them in the module rather than discarding them.
extern "C" int pthread_setname_np(pthread_t thread, const char *name)
{
    std::lock_guard<std::mutex> guard(names_mutex);
    thread_names[thread] = name;
    return 0;
}

extern "C" int pthread_getname_np(pthread_t thread, char *name, size_t size)
{
    std::lock_guard<std::mutex> guard(names_mutex);
    if (!size) { return 34; }
    const auto found = thread_names.find(thread);
    const std::string value = found == thread_names.end() ? "browser" : found->second;
    std::strncpy(name, value.c_str(), size-1);
    name[size-1] = '\0';
    return 0;
}

extern "C" EMSCRIPTEN_KEEPALIVE int tw_init()
{
    px4::init_once();
    init_app_map(applications);
    return 0;
}

extern "C" EMSCRIPTEN_KEEPALIVE int tw_command(const char *command)
{
    std::istringstream input(command);
    std::vector<std::string> tokens;
    std::string token;
    while (input >> token) { tokens.push_back(token); }
    if (tokens.empty()) { return -1; }
    auto app = applications.find(tokens[0]);
    if (app == applications.end()) { return -2; }
    std::vector<char *> argv;
    for (auto &text : tokens) { argv.push_back(&text[0]); }
    argv.push_back(nullptr);
    optind = 1;
    return app->second(static_cast<int>(tokens.size()), argv.data());
}

int main() { return 0; }

static std::atomic<int> command_result{0};
extern "C" EMSCRIPTEN_KEEPALIVE int tw_command_async(const char *command)
{
    if (command_result.load()==INT_MIN) { return -1; }
    command_result.store(INT_MIN);
    const std::string copy(command);
    std::thread([copy] { command_result.store(tw_command(copy.c_str())); }).detach();
    return 0;
}
extern "C" EMSCRIPTEN_KEEPALIVE int tw_command_result() { return command_result.load(); }
