# File này gom tất cả model lại một chỗ, để nơi khác chỉ cần
# "from app.models import Document, FormulaEntry, User, Log"
# thay vì phải nhớ đường dẫn tới từng file con.
# Đồng thời, đây cũng là lý do Alembic (bước 4) "nhìn thấy" đủ 4 bảng khi generate migration.

from app.models.document import Document
from app.models.formula_entry import FormulaEntry
from app.models.user import User
from app.models.log import Log