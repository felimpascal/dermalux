from app.common.errors import AppError
from app.modules.user_mgmt.repository import UserMgmtRepository

# PAKAI HASH YANG SAMA DENGAN AUTH
from app.modules.auth.repository import sha256


class UserMgmtService:
    @staticmethod
    def list_users(q: str = ""):
        return UserMgmtRepository.list_users(q=q)

    @staticmethod
    def get_user(user_id: int):
        row = UserMgmtRepository.get_user(user_id)
        if not row:
            raise AppError("User tidak ditemukan", 404)
        return row

    @staticmethod
    def create_user(data: dict):
        nama = (data.get("nama") or "").strip()
        username = (data.get("username") or "").strip()
        role = (data.get("role") or "user").strip()
        is_active = int(data.get("is_active") or 0)
        password = (data.get("password") or "").strip()

        if not nama:
            raise AppError("nama wajib diisi", 400)

        if not username:
            raise AppError("username wajib diisi", 400)

        if not password or len(password) < 6:
            raise AppError("password minimal 6 karakter", 400)

        password_hash = sha256(password)

        try:
            UserMgmtRepository.insert_user(
                nama=nama,
                username=username,
                password_hash=password_hash,
                role=role,
                is_active=is_active,
            )
        except Exception as e:
            raise AppError(f"Gagal membuat user: {str(e)}", 400)

    @staticmethod
    def update_user(user_id: int, data: dict):
        nama = (data.get("nama") or "").strip()
        username = (data.get("username") or "").strip()
        role = (data.get("role") or "user").strip()
        is_active = int(data.get("is_active") or 0)

        if not nama:
            raise AppError("nama wajib diisi", 400)

        if not username:
            raise AppError("username wajib diisi", 400)

        try:
            UserMgmtRepository.update_user(
                user_id=user_id,
                nama=nama,
                username=username,
                role=role,
                is_active=is_active,
            )
        except Exception as e:
            raise AppError(f"Gagal mengupdate user: {str(e)}", 400)

    @staticmethod
    def reset_password(user_id: int, password: str):
        password = (password or "").strip()
        if not password or len(password) < 6:
            raise AppError("password minimal 6 karakter", 400)

        password_hash = sha256(password)
        UserMgmtRepository.update_password(user_id, password_hash)

    @staticmethod
    def get_permissions_with_granted(user_id: int):
        return UserMgmtRepository.get_permissions_with_granted(user_id)

    @staticmethod
    def replace_permissions(user_id: int, perm_ids: list[str]):
        clean_ids: list[int] = []
        for x in perm_ids:
            x = (x or "").strip()
            if x.isdigit():
                clean_ids.append(int(x))
        UserMgmtRepository.replace_permissions(user_id, clean_ids)

    @staticmethod
    def get_user_by_public_id(public_id: str):
        row = UserMgmtRepository.get_user_by_public_id(public_id)
        if not row:
            raise AppError("User tidak ditemukan", 404)
        return row