"""Apply the web patches (emscripten build) to a fresh copy of master's engine/ in src-v2/engine."""
import sys, re
root = sys.argv[1] + '/engine/'
def edit(rel, old, new, count=1):
    p = root + rel
    t = open(p, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in t else '\n'
    old_, new_ = old.replace('\n', nl), new.replace('\n', nl)
    assert t.count(old_) == count, (rel, old[:60], t.count(old_))
    t = t.replace(old_, new_)
    open(p, 'w', encoding='utf-8', newline='').write(t)
edit('fx/ConvolverIr.cpp', "std::to_string(se ? 0 : size) + '|' + std::to_string(te ? 0 : time.time_since_epoch().count())",
     "std::to_string(static_cast<unsigned long long>(se ? 0 : size)) + '|' + std::to_string(static_cast<long long>(te ? 0 : time.time_since_epoch().count()))")
edit('instruments/SamplerFiles.cpp', "}  // namespace as::smp\n", """}  // namespace as::smp

#ifdef __EMSCRIPTEN__
#include <emscripten.h>
// web build: drop every decoded sample (the browser keeps the compressed files and loads a piece's set anew)
extern "C" EMSCRIPTEN_KEEPALIVE void as_clear_sample_cache() {
    std::lock_guard<std::mutex> lock(as::smp::gMutex);
    as::smp::cache().clear();
}
#endif
""")
edit('main.cpp', "#include <windows.h>\n#include <shellapi.h>\n", "#ifdef _WIN32\n#include <windows.h>\n#include <shellapi.h>\n#endif\n")
edit('main.cpp', """    wchar_t buffer[MAX_PATH];
    const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    return fs::path(std::wstring(buffer, length)).parent_path();
""", """#ifdef _WIN32
    wchar_t buffer[MAX_PATH];
    const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    return fs::path(std::wstring(buffer, length)).parent_path();
#else
    return fs::current_path();
#endif
""")
p = root + 'main.cpp'
t = open(p, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in t else '\n'
i = t.index('std::vector<std::string> utf8Args(int argc, char** argv) {')
j = t.index('    std::vector<std::string> out;', i) + len('    std::vector<std::string> out;')
t = t[:j] + nl + '#ifndef _WIN32' + nl + '    out.assign(argv + 1, argv + argc);' + nl + '    return out;' + nl + '#else' + t[j:]
k = t.index('    if (w) LocalFree(w);' + nl + '    return out;' + nl, j) + len('    if (w) LocalFree(w);' + nl + '    return out;' + nl)
t = t[:k] + '#endif' + nl + t[k:]
open(p, 'w', encoding='utf-8', newline='').write(t)
edit('render/Renderer.cpp', "namespace as {\nnamespace {\n", """#ifdef __EMSCRIPTEN__
#include <emscripten.h>
// web build: stream the master output to JS (Module.onStream(L, R, done)) in ~0.75 s chunks while rendering
EM_JS(void, as_js_stream, (const float* l, const float* r, int n, int done), {
    if (Module["onStream"]) Module["onStream"](HEAPF32.slice(l >> 2, (l >> 2) + n), HEAPF32.slice(r >> 2, (r >> 2) + n), done);
});
namespace {
struct StreamBuf {
    std::vector<float> l, r;
    void push(const float* a, const float* b, int n) {
        if (l.capacity() < 40000) { l.reserve(40000); r.reserve(40000); }
        l.insert(l.end(), a, a + n); r.insert(r.end(), b, b + n);
        if (l.size() >= 32768) flush(0);
    }
    void flush(int done) { as_js_stream(l.data(), r.data(), static_cast<int>(l.size()), done); l.clear(); r.clear(); }
};
StreamBuf gStream;
}  // namespace
#endif

namespace as {
namespace {
""")
edit('render/Renderer.cpp', "            mix.write(mixL.data(), mixR.data(), count);\n",
     "            mix.write(mixL.data(), mixR.data(), count);\n#ifdef __EMSCRIPTEN__\n            gStream.push(mixL.data(), mixR.data(), count);\n#endif\n")
edit('render/Renderer.cpp', "    mix.close();\n", "#ifdef __EMSCRIPTEN__\n    gStream.flush(1);\n#endif\n    mix.close();\n")
print('patched')
