/**
 * Master Obat Module
 * Dipanggil setelah modal master_obat_modal.html di-load
 */

let dtMasterObat = null;

function initMasterObat() {

    // ===============================
    // CEGAH DOUBLE INIT
    // ===============================
    if ($.fn.DataTable.isDataTable("#tblObat")) {
        dtMasterObat.destroy();
        $("#tblObat tbody").empty();
    }

    // ===============================
    // INIT DATATABLE
    // ===============================
    dtMasterObat = $("#tblObat").DataTable({
        paging: false,
        searching: true,
        info: true,
        lengthChange: false,
        autoWidth: false,

        columns: [
            { data: "ID" },
            { data: "NamaObat" },
            { data: "Kemasan" },
            { data: "IsiKms" },
            { data: "Unit" },
            {
                data: "HargaPub",
                className: "text-end",
                render: $.fn.dataTable.render.number(",", ".", 0)
            },
            {
                data: "HargaInaN",
                className: "text-end",
                render: $.fn.dataTable.render.number(",", ".", 0)
            },
            {
                data: "Status",
                className: "text-center"
            },
            {
                data: null,
                className: "text-center",
                orderable: false,
                render: function (data, type, row) {
                    const isEnable = (row.Status || "").toLowerCase() === "enable";
                    return `
                        <button class="btn btn-sm ${isEnable ? "btn-outline-danger" : "btn-outline-success"} btn-toggle-status">
                            ${isEnable ? "Disabled" : "Enable"}
                        </button>
                    `;
                }
            }
        ]
    });

    // ===============================
    // LOAD DATA
    // ===============================
    function loadMasterObat() {
        $.get("/apotik/api/obat/list")
            .done(function (resp) {
                dtMasterObat.clear().rows.add(resp.data || []).draw();

                // default tampilkan Enable
                showEnableOnly();
            })
            .fail(function () {
                window.myAlert("Gagal memuat master obat", "error");
            });
    }

    // ===============================
    // FILTER STATUS
    // ===============================
    function showEnableOnly() {
        dtMasterObat.column(7).search("^Enable$", true, false).draw();
        $("#btnShowEnable")
            .addClass("btn-primary")
            .removeClass("btn-outline-secondary");
        $("#btnShowDisabled")
            .addClass("btn-outline-secondary")
            .removeClass("btn-primary");
    }

    function showDisabledOnly() {
        dtMasterObat.column(7).search("^Disabled$", true, false).draw();
        $("#btnShowDisabled")
            .addClass("btn-primary")
            .removeClass("btn-outline-secondary");
        $("#btnShowEnable")
            .addClass("btn-outline-secondary")
            .removeClass("btn-primary");
    }

    // ===============================
    // EVENT BINDING (OFF → ON)
    // ===============================
    $("#btnShowEnable").off().on("click", showEnableOnly);
    $("#btnShowDisabled").off().on("click", showDisabledOnly);

    $("#btnRefreshObat").off().on("click", loadMasterObat);

    $("#txtFilterNamaObat").off().on("keyup change", function () {
        dtMasterObat.column(1).search(this.value).draw();
    });

    // ===============================
    // TOGGLE STATUS
    // ===============================
    $("#tblObat tbody")
        .off("click", ".btn-toggle-status")
        .on("click", ".btn-toggle-status", function () {

            const rowApi = dtMasterObat.row($(this).closest("tr"));
            const row = rowApi.data();
            if (!row) return;

            const newStatus =
                (row.Status || "").toLowerCase() === "enable"
                    ? "Disabled"
                    : "Enable";

            Swal.fire({
                icon: "question",
                title: "Konfirmasi",
                html: `
                    Ubah status obat:<br>
                    <strong>${row.NamaObat}</strong><br>
                    menjadi <strong>${newStatus}</strong>?
                `,
                showCancelButton: true,
                confirmButtonText: "Ya, Ubah",
                cancelButtonText: "Batal"
            }).then((res) => {
                if (!res.isConfirmed) return;

                $.ajax({
                    url: "/apotik/api/obat/update_status",
                    method: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({
                        id: row.ID,
                        status: newStatus
                    }),
                    success: function (resp) {
                        if (resp && resp.success) {
                            row.Status = newStatus;
                            rowApi.data(row).invalidate().draw(false);
                            window.myAlert("Status obat berhasil diperbarui", "success");
                        } else {
                            window.myAlert(
                                resp.error || "Gagal memperbarui status obat",
                                "error"
                            );
                        }
                    },
                    error: function () {
                        window.myAlert("Terjadi kesalahan server", "error");
                    }
                });
            });
        });

    // ===============================
    // INITIAL LOAD
    // ===============================
    loadMasterObat();
}
