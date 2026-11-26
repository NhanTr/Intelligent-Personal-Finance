# Cấu hình GitHub dành cho Nhân (chủ repo)

Repo: https://github.com/NhanTr/Intelligent-Personal-Finance

`KhoaTryHard` có quyền Write để đẩy nhánh và mở PR. Phần Settings dưới đây cần
`NhanTr` đăng nhập bằng tài khoản chủ repo. Không chia sẻ token hay mật khẩu.

## 1. Thứ tự khởi tạo để không khóa PR đầu tiên

1. Khoa tạo `develop` từ `main`, đẩy nhánh phiên bản và mở PR thiết lập vào `develop`.
2. Nhân review PR; kiểm tra `branch-policy` và `python-tests` cùng đạt trên commit mới nhất.
3. Nhân chọn **Squash and merge** PR vào `develop`, giữ nhánh phiên bản.
4. Khoa hoặc Nhân mở PR **develop → main**; người còn lại review, kiểm tra CI và chọn
   **Create a merge commit**. Việc này đưa workflow lên cả hai nhánh nền.
5. Sau khi hai PR hoàn tất, Nhân áp dụng Settings và hai ruleset bên dưới.
6. Nhân thêm Duy vào **Settings → Collaborators**, quyền Write, bằng đúng tài khoản
   GitHub do Duy cung cấp. Duy phải nhận lời mời trước khi được giao review.

Không bật required checks trước khi workflow đã chạy để GitHub nhận đúng tên check.
Không tự duyệt PR của mình. Các PR chức năng sau thiết lập theo phân công trong CONTRIBUTING.

## 2. Áp dụng cấu hình bằng GitHub CLI

Chạy tại bản clone đã cập nhật `origin/develop`, với tài khoản **NhanTr** đang active.
`gh auth status` cho biết tài khoản; dừng nếu tài khoản active không phải chủ repo.

```powershell
gh auth status
gh api repos/NhanTr/Intelligent-Personal-Finance --jq '.permissions'

# Nhánh mặc định và phương thức merge; giữ nguyên nhánh sau merge
gh api --method PATCH repos/NhanTr/Intelligent-Personal-Finance --input .github/repository-settings.json

# Xem các ruleset trước để tránh tạo bản trùng
gh api repos/NhanTr/Intelligent-Personal-Finance/rulesets --jq '.[] | {id,name,enforcement}'

# Chỉ POST khi chưa có ruleset cùng tên
gh api --method POST repos/NhanTr/Intelligent-Personal-Finance/rulesets --input .github/rulesets/develop.json
gh api --method POST repos/NhanTr/Intelligent-Personal-Finance/rulesets --input .github/rulesets/main.json
```

Nếu ruleset đã tồn tại, lấy `id` ở lệnh liệt kê, rồi **PUT** cùng file vào
`repos/NhanTr/Intelligent-Personal-Finance/rulesets/<id>` để cập nhật. Không POST
thêm bản trùng, không xóa rule khác đang có. Nếu API trả 403/404, kiểm tra tài khoản
và quyền; không coi file đã commit là cấu hình đang hoạt động.

## 3. Cấu hình tương đương trên giao diện

Trong **Settings → General**: default branch `develop`; bật Squash merge và Merge
commits; tắt Rebase merge và Automatically delete head branches.

Trong **Settings → Rules → Rulesets**, tạo hai **Branch ruleset**:

| Thiết lập | protect-develop | protect-main |
|---|---|---|
| Enforcement | Active | Active |
| Target | `develop` | `main` |
| Bypass list | Rỗng | Rỗng |
| Restrict deletions | Bật | Bật |
| Block force pushes | Bật | Bật |
| Require a pull request before merging | Bật | Bật |
| Required approvals | 1 | 1 |
| Dismiss stale approvals when new commits are pushed | Bật | Bật |
| Require conversation resolution | Bật | Bật |
| Require status checks | `branch-policy`, `python-tests` | `branch-policy`, `python-tests` |
| Require branches to be up to date before merging | Bật | Tắt |

Không bật linear history: PR `develop → main` cần Merge commit. Không bật Require
code owner review khi chưa có danh sách tài khoản và phân công CODEOWNERS phù hợp.
Rule không tự phân công reviewer hay giới hạn người merge chỉ là Khoa; việc review
theo phân công nhóm. GitHub không cho tác giả tự approve PR của mình.

Hai phương thức merge được bật ở cấp repo. Chọn **Squash** cho nhánh công việc →
`develop`, **Merge commit** cho `develop` → `main`. `branch-policy` kiểm tra nguồn
và đích PR; rule này không xác định được nút merge mà người dùng sẽ chọn sau đó.

## 4. Đọc lại và kiểm chứng

```powershell
gh api repos/NhanTr/Intelligent-Personal-Finance --jq '{default_branch,allow_squash_merge,allow_merge_commit,allow_rebase_merge,delete_branch_on_merge}'
gh api repos/NhanTr/Intelligent-Personal-Finance/rulesets --jq '.[] | {id,name,enforcement}'
gh api repos/NhanTr/Intelligent-Personal-Finance/rules/branches/develop
gh api repos/NhanTr/Intelligent-Personal-Finance/rules/branches/main
gh api repos/NhanTr/Intelligent-Personal-Finance/branches --jq '.[] | {name,protected}'
```

Đọc cả chi tiết ruleset theo ID nếu cần kiểm tra bypass. Kết quả phải cho thấy:
`develop` mặc định; cả hai nhánh được bảo vệ; hai ruleset Active, bypass rỗng, một
approval, dismiss stale, giải quyết hội thoại và đúng hai required checks; strict
status checks bật ở develop, tắt ở main. Giữ nguyên các nhánh lịch sử.

Ở PR công việc kế tiếp, kiểm tra giao diện GitHub yêu cầu đủ approval/check và chặn
merge khi thiếu; PR sai đích phải có `branch-policy` thất bại. Không thử force push
hoặc xóa nhánh nền để kiểm tra. Chỉ xác nhận thiết lập hoàn tất sau khi đọc lại
Settings và xác minh trạng thái PR. Nếu Settings còn chờ Nhân, ghi rõ đang chờ.
