# Quy trình cộng tác — Nhóm Khoa, Nhân, Duy

Luồng tích hợp: **nhánh công việc → develop → main**. `develop` là nhánh mặc định
và nơi tích hợp; `main` là bản ổn định đã nghiệm thu. Các thay đổi đi qua PR.

## 1. Nhận việc và tạo một nhánh mới

Mỗi issue ghi mã gói, người làm, người rà soát, hạn, phụ thuộc và tiêu chí nghiệm thu.
Theo [phân công nhóm](plans/team-work-packages.md):

| Người làm | Mã gói | Rà soát |
|---|---|---|
| Khoa | K1–K4 | Duy; Nhân kiểm tra phần liên quan ML |
| Nhân | N1–N4 | Khoa |
| Duy | D1–D4 | Nhân; Khoa duyệt tích hợp |

Tên nhánh: `<loại>/<thành-viên>-<mã-việc>-<mô-tả>-YYYYMMDD-HHMMSS`.
Loại hợp lệ: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.
Thành viên: `khoa`, `nhan`, `duy`; mã gói viết thường và đúng người (`k2`, `n3`, `d2`).
Mô tả dùng chữ thường không dấu, chữ số và dấu `-`.

Timestamp lấy theo **Asia/Saigon**, tạo trước khi sửa code để lưu từng phiên bản.
Check chấp nhận cả tên nhánh không có timestamp để tương thích quy ước gói việc;
nhóm vẫn thêm timestamp cho các phiên bản mới và giữ nhánh cũ trên GitHub.
Nhánh thiết lập ban đầu có dạng `chore/khoa-repo-workflow-YYYYMMDD-HHMMSS`.

Ví dụ PowerShell cho Khoa (Nhân/Duy đổi tên và mã gói tương ứng):

```powershell
git clone https://github.com/NhanTr/Intelligent-Personal-Finance.git
cd Intelligent-Personal-Finance
git fetch origin
$stamp = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow, 'SE Asia Standard Time').ToString('yyyyMMdd-HHmmss')
$branch = "feat/khoa-k2-import-csv-$stamp"
git switch -c $branch origin/develop
```

Nếu đã có bản clone, bắt đầu từ `git fetch origin`; bảo đảm không có thay đổi chưa
lưu trước khi chuyển nhánh. Mỗi đầu việc tạo nhánh mới từ `origin/develop`, không
tái sử dụng nhánh đã merge. Nhánh lịch sử `feat/nhan-ml-pipeline` được giữ nguyên;
công việc ML mới dùng nhánh mới theo quy ước trên.

## 2. Làm việc, kiểm thử và mở PR

Chỉ sửa phạm vi issue đang nhận. Khi đổi schema phải cập nhật đồng bộ API, CSV,
đặc trưng và hợp đồng tích hợp. Không đưa dữ liệu cá nhân chưa ẩn danh vào repo.

```powershell
# Dùng cùng lệnh với GitHub Actions, Python 3.12 và uv.lock
python scripts/ci/run_tests.py

# Kiểm tra luồng nhánh tại máy; thay tên nhánh trong ví dụ bằng tên thực tế
python scripts/ci/branch_policy.py --repository NhanTr/Intelligent-Personal-Finance --base develop --head $branch --base-repository NhanTr/Intelligent-Personal-Finance --head-repository NhanTr/Intelligent-Personal-Finance

# Chỉ stage các file thuộc đầu việc (thay đường dẫn minh họa bằng file thực tế)
git add path/to/changed-file
git commit -m "feat(k2): import transactions from CSV"
git push -u origin $branch

# Sau push, so SHA local và remote để xác nhận phiên bản đã lưu
git rev-parse HEAD
git ls-remote --heads origin $branch
gh pr create --base develop --head $branch
```

Điền mẫu PR: mã việc, thay đổi, lệnh và kết quả kiểm thử, ảnh hưởng tích hợp,
tài liệu và người rà soát. Trên GitHub chọn đúng **base: develop**, **compare: nhánh của mình**.

Hai check bắt buộc là `branch-policy` và `python-tests`. CI chạy khi mở, cập nhật,
mở lại, đổi đích hoặc chuyển PR sang sẵn sàng review; test cũng chạy khi push vào
`develop`/`main`. Check thất bại phải được sửa trước khi merge. Bộ test tự động
không chạy lệnh mở khóa tập đánh giá ML cuối kỳ.

## 3. Nhận review và xử lý conflict trên chính nhánh PR

Không tự duyệt phần mình. Khoa duyệt tích hợp; PR chức năng của Khoa do Duy review,
Nhân kiểm tra phần ML liên quan. Riêng PR thiết lập quy trình do **Nhân review**.

Mọi sửa lỗi theo review và giải quyết conflict nằm trên chính nhánh PR đang mở:

```powershell
git switch $branch
git fetch origin
git merge origin/develop
# Nếu có conflict: sửa từng file, bỏ marker conflict rồi stage các file đã xử lý
git add path/to/resolved-file
git commit
python scripts/ci/run_tests.py
git push origin $branch
```

Chỉ chạy `git commit` ở bước conflict khi Git yêu cầu hoàn tất merge; nếu merge đã
tự tạo commit thì chuyển sang kiểm thử. Dùng `git merge --abort` nếu cần hủy merge
đang conflict. Không force push. Nhánh phải cập nhật với `develop`, các hội thoại
đã giải quyết, hai check đạt và có ít nhất một approval hợp lệ trước khi merge.
Thay đổi mới làm approval cũ mất hiệu lực, cần review lại.

PR công việc vào `develop`: chọn **Squash and merge**. Giữ nhánh phiên bản sau merge.
Chỉ đánh dấu issue hoàn thành khi có sản phẩm, kiểm thử, tài liệu và người review xác nhận.

## 4. Đưa bản tích hợp vào main

Sau khi nhóm nghiệm thu, mở PR từ `develop` của chính repo vào `main`:

```powershell
gh pr create --base main --head develop --title "Release: bản tích hợp đã nghiệm thu"
```

PR cần người khác review, hai check đạt và hết hội thoại chưa giải quyết. Chọn
**Create a merge commit** để giữ lịch sử `develop`; không squash/rebase PR phát hành.
`main` không nhận trực tiếp nhánh chức năng hay `develop` từ fork.

GitHub không lưu nhánh gốc lúc tạo nhánh; lệnh ở bước 1 bảo đảm xuất phát từ
`origin/develop`. Rule kiểm tra nguồn/đích PR và yêu cầu cập nhật với nhánh tích hợp.
Các thành viên có quyền Write có thể chọn phương thức merge ở giao diện; người
duyệt chịu trách nhiệm chọn Squash cho công việc, Merge commit cho phát hành.

## 5. Thiết lập GitHub cần Nhân thực hiện

Nhân áp dụng [hướng dẫn Settings và ruleset](docs/contributing/github-settings.md)
sau khi các check của PR khởi tạo đã đạt. File cấu hình trong repo chỉ là cấu hình
để áp dụng, không tự bật bảo vệ nhánh. Nhân thêm tài khoản GitHub của Duy với quyền
Write trước khi giao review. Không tự ý đổi quyền hoặc bỏ rule để merge PR lỗi.

Nguồn phân công: [kế hoạch trên Drive](https://docs.google.com/document/d/1oGoeUg09HoRTcs4KOzMxtQtDFUYmvS3K/edit)
và [kế hoạch trong repo](plans/README.md).
