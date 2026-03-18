from app.common.errors import AppError
from .repository import AuthRepository, sha256


class AuthService:
    @staticmethod
    def login_form(username: str, password: str) -> dict:
        username = (username or "").strip()
        password = (password or "").strip()

        if not username or not password:
            raise AppError("User/Password wajib diisi.", 400)

        user = AuthRepository.get_user_by_username(username)
        if not user:
            # Sesuai style pesan template Anda
            raise AppError("User Tidak Ditemukan!", 401)

        if int(user.get("is_active") or 0) != 1:
            raise AppError("User Tidak Aktif!", 401)

        if sha256(password) != (user.get("password_hash") or ""):
            raise AppError("Password Salah!", 401)

        return {
            "id": int(user["id"]),
            "username": user["username"],
            "nama": user["nama"],
            "role": user.get("role") or "user",
        }

    @staticmethod
    def change_password(user_id: int, username: str, pass_lama: str, pass_baru: str, pass_konfirmasi: str) -> None:
        username = (username or "").strip()
        pass_lama = (pass_lama or "").strip()
        pass_baru = (pass_baru or "").strip()
        pass_konfirmasi = (pass_konfirmasi or "").strip()
        print (user_id)

        if not username:
            raise AppError("Session user tidak valid. Silakan login ulang.", 401)

        if not pass_lama or not pass_baru or not pass_konfirmasi:
            raise AppError("Semua field password wajib diisi.", 400)

        if pass_baru != pass_konfirmasi:
            raise AppError("Password Baru Tidak Sesuai dengan Password Konfirmasi!", 400)

        if len(pass_baru) < 8:
            raise AppError("Password baru minimal 8 karakter.", 400)

        user = AuthRepository.get_user_by_username(username)
        if not user:
            raise AppError("User Tidak Ditemukan!", 404)

        if int(user["id"]) != int(user_id):
            raise AppError("Session user tidak valid. Silakan login ulang.", 401)

        if sha256(pass_lama) != (user.get("password_hash") or ""):
            raise AppError("Password Lama Salah!", 400)

        AuthRepository.update_password(int(user_id), pass_baru)