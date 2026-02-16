# Performance Improvement Recommendations

> **Analysis Date**: 2026-02-16
> **Target Release**: v43.0 or later
> **Full Details**: See `docs/PERFORMANCE_ANALYSIS.md`

## Quick Summary

Systematic analysis identified **15 performance issues** across 12 files, ranging from critical GUI-blocking operations to optimization opportunities.

**Total Potential Impact**:
- **-2 seconds** startup time reduction
- **-80%** database operation overhead
- **-70%** process monitoring I/O
- **Zero GUI freezes** from blocking operations

---

## Critical Issues (Fix Immediately)

| # | Issue | File | Impact | Effort |
|---|-------|------|--------|--------|
| 1 | Blocking `os.listdir()` in UI | `ui/wizard.py:90` | GUI freeze on first run | 2 hours |
| 2 | No database connection pooling | `utils/health_timeline.py:50-66` | 80% slower metrics | 3 hours |
| 3 | Sync network I/O in `__init__` | `ui/community_tab.py:113` | 1.5s tab load time | 2 hours |

**Estimated Total Effort**: 1 day
**User Impact**: High (eliminates GUI freezes, major speedup)

---

## High Priority Issues (Next Sprint)

| # | Issue | File | Impact | Effort |
|---|-------|------|--------|--------|
| 4 | Repeated `shutil.which()` calls | `safety.py:52-54` + others | 90% wasted lookups | 1 hour |
| 5 | Redundant DNF lock checks | `utils/safety.py:29` | 50% excess validation | 1 hour |
| 6 | Full process scan every 2s | `ui/monitor_tab.py:732` | 70% excess I/O | 3 hours |
| 7 | `SystemManager` no caching | Multiple files | 100+ file checks | 30 min |
| 8 | Sequential HTTP in marketplace | `utils/plugin_marketplace.py:191` | 80% slower listing | 2 hours |

**Estimated Total Effort**: 2 days
**User Impact**: Medium (noticeable responsiveness improvement)

---

## Implementation Plan

### Phase 1: Critical Fixes (Immediate)

**Target**: Eliminate all blocking operations in UI layer

**Changes**:
1. **Wizard async GPU detection** (`ui/wizard.py`)
   - Move `os.listdir("/sys/class/drm/")` to `QThread`
   - Add loading spinner during detection
   - Test: Verify GUI remains responsive

2. **Database connection pooling** (`utils/health_timeline.py`)
   - Change `_get_conn()` to reuse connection
   - Enable SQLite WAL mode
   - Add `__del__` cleanup
   - Test: Benchmark 100 consecutive writes (<1s total)

3. **Deferred marketplace loading** (`ui/community_tab.py`)
   - Move `refresh_marketplace()` out of `__init__`
   - Use `QTimer.singleShot(100, ...)` to defer
   - Show loading indicator
   - Test: Tab should appear instantly

**Success Criteria**:
- No `subprocess.run()` or blocking I/O in any `ui/` file
- All tabs load in <200ms
- Performance tests pass

---

### Phase 2: Caching Layer (Next Sprint)

**Target**: Eliminate redundant system calls

**Changes**:
1. **Create `utils/cache.py`**
   ```python
   from functools import lru_cache, wraps
   import time

   @lru_cache(maxsize=32)
   def which_cached(cmd: str) -> Optional[str]:
       return shutil.which(cmd)

   def ttl_cache(seconds: int):
       """Time-based cache decorator."""
       # Implementation in PERFORMANCE_ANALYSIS.md
   ```

2. **Add caching to SystemManager** (`utils/system.py`)
   - `@lru_cache` on `get_package_manager()`
   - `@lru_cache` on `is_atomic()`

3. **Cache DNF lock checks** (`utils/safety.py`)
   - Add 5-second TTL cache to `check_dnf_lock()`

4. **Replace all `shutil.which()` calls**
   - Global find/replace: `shutil.which(` → `which_cached(`
   - Import `from utils.cache import which_cached`

5. **Concurrent marketplace fetching** (`utils/plugin_marketplace.py`)
   - Use `ThreadPoolExecutor` for parallel HTTP
   - Limit to 5 concurrent requests

**Success Criteria**:
- Zero repeated `shutil.which()` calls within 60 seconds
- Marketplace loads 5 plugins in <300ms (vs 1000ms)

---

### Phase 3: Process Monitoring Optimization (Future)

**Target**: Reduce I/O overhead

**Changes**:
1. **Differential process updates** (`utils/process_manager.py`)
   - Track `_last_pids` set
   - Only read `/proc/PID/` for new/changed processes
   - Return `(updated, new_pids, removed_pids)` tuple

2. **Update monitor tab** (`ui/monitor_tab.py`)
   - Use differential API
   - Update only changed rows in table

**Success Criteria**:
- Process refresh <100ms (from ~200ms)
- Reduced `/proc` reads by 70%

---

## Testing Strategy

### 1. Performance Regression Tests

Create `tests/test_performance.py`:
- `test_database_connection_reuse()` - <1s for 100 writes
- `test_process_listing_cache()` - Warm call <50% of cold
- `test_which_caching()` - 1000 calls in <0.1s
- `test_no_blocking_in_ui()` - Static analysis of ui/ imports

### 2. Startup Profiling

```bash
# Before optimization
python scripts/profile_startup.py > before.txt

# After optimization
python scripts/profile_startup.py > after.txt

# Compare
diff before.txt after.txt
```

### 3. Manual Testing Checklist

- [ ] First-run wizard appears instantly (no freeze)
- [ ] Community tab loads in <300ms
- [ ] Monitor tab refreshes smoothly every 2 seconds
- [ ] No GUI freezes during any operation
- [ ] Memory usage stable over 30-minute session

---

## Files Changed Summary

### Must Modify (Phase 1)
- `loofi-fedora-tweaks/ui/wizard.py` - Async GPU detection
- `loofi-fedora-tweaks/ui/community_tab.py` - Deferred loading
- `loofi-fedora-tweaks/utils/health_timeline.py` - Connection pooling

### Should Modify (Phase 2)
- `loofi-fedora-tweaks/utils/cache.py` - **NEW FILE** (caching utilities)
- `loofi-fedora-tweaks/utils/system.py` - Add @lru_cache
- `loofi-fedora-tweaks/utils/safety.py` - Cache DNF checks
- `loofi-fedora-tweaks/utils/plugin_marketplace.py` - Concurrent HTTP
- 20+ files - Replace `shutil.which()` → `which_cached()`

### Could Modify (Phase 3)
- `loofi-fedora-tweaks/utils/process_manager.py` - Differential updates
- `loofi-fedora-tweaks/ui/monitor_tab.py` - Use differential API

### New Test Files
- `tests/test_performance.py` - Performance regression suite
- `tests/test_caching.py` - Cache behavior validation

### New Scripts
- `scripts/profile_startup.py` - Startup time profiler

---

## Success Metrics

### Before Optimization (Baseline)
- Cold startup: ~5 seconds
- First-run wizard: 500ms freeze
- Community tab load: 1.5 seconds
- Process refresh: 200ms
- Database write: 15ms

### After Phase 1 (Target)
- Cold startup: ~3 seconds ✅
- First-run wizard: 0ms freeze ✅
- Community tab load: <200ms ✅
- Process refresh: 200ms (unchanged)
- Database write: 3ms ✅

### After Phase 2 (Target)
- Cold startup: ~3 seconds
- First-run wizard: 0ms freeze
- Community tab load: <200ms
- Process refresh: 200ms (unchanged)
- Database write: 3ms
- Tool lookups: <0.1ms (cached) ✅
- Marketplace: 300ms for 5 plugins ✅

### After Phase 3 (Target)
- All Phase 2 targets
- Process refresh: <100ms ✅

---

## Risk Assessment

### Low Risk Changes
- Adding `@lru_cache` to pure functions
- Database connection pooling (well-tested pattern)
- Caching `shutil.which()` results

### Medium Risk Changes
- Moving blocking I/O to threads (requires careful signal handling)
- Concurrent HTTP requests (thread safety concerns)
- Differential process updates (complex state management)

### Testing Requirements
- All changes must have unit tests
- Manual testing on both traditional and atomic Fedora
- Performance benchmarks must show improvement
- No regressions in functionality

---

## Next Steps

1. **Review** this document with maintainers
2. **Approve** Phase 1 implementation scope
3. **Create** tracking issues for each phase
4. **Implement** Phase 1 critical fixes
5. **Validate** with performance test suite
6. **Document** in CHANGELOG.md
7. **Release** in next version (v43.0 or v42.1 hotfix)

---

## References

- Full analysis: `docs/PERFORMANCE_ANALYSIS.md`
- Architecture rules: `ARCHITECTURE.md`
- Testing guidelines: `.github/instructions/test.instructions.md`
