# Feature Spec: n8n Version Upgrade (v1.72.0 -> v2.9.4)

## 1. Overview
The goal of this task is to upgrade the n8n automation engine from v1.72.0 to the latest stable version v2.9.4 (as of March 2, 2026). This upgrade ensures the system benefits from the latest security patches, performance optimizations, and the new "Publish/Save" paradigm introduced in n8n 2.0.

## 2. Technical Goals
- **Modernization**: Transition from v1.x to v2.x.
- **Stability**: Resolve any potential legacy bugs in the outdated v1 image.
- **Security**: Enable the new default security task runners and sandboxing.

## 3. Impact Analysis
### 3.1 Breaking Changes in v2.0
- **Publish/Save Paradigm**: Workflows must be explicitly "Published" to go live.
- **Start Node Removal**: Existing workflows must use `Manual Trigger` or specialized trigger nodes. (Current workflows already use `manualTrigger` and `scheduleTrigger`, so impact is minimal).
- **Subworkflow Data**: Data returned from subworkflows now overrides input data. (Not currently using subworkflows, no impact).
- **Security Defaults**: Code nodes are sandboxed by default.

### 3.2 System Integration
- **Public API v1**: n8n v2 still supports Public API v1, which our `AutomationService` uses.
- **Docker Compose**: Only the image tag needs to be updated.

## 4. Implementation Steps
1. **Backup**: Perform a full recursive copy of `./data/n8n_data` to a backup directory.
2. **Configuration**: Update `docker-compose.yml` with the new image tag `docker.n8n.io/n8nio/n8n:2.9.4`.
3. **Migration**: Restart the n8n container and allow it to run internal database migrations.
4. **Verification**: 
    - Check n8n logs for migration errors.
    - Verify workflow visibility via the Dashboard.
    - Test deployment of a sample workflow.

## 5. Risk Mitigation
- **Rollback Plan**: If the migration fails, revert `docker-compose.yml` to v1.72.0 and restore the `./data/n8n_data` backup.
