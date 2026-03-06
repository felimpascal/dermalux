/**
 * Master Tarif Module
 */

let dtMasterTarif = null;

function initMasterTarif() {

    // cegah double init
    if ($.fn.DataTable.isDataTable("#tblTarif")) {
        dtMasterTarif.destroy();
        $("#tblTarif tbody").empty();
    }

    dtMasterTarif = $("#tblTarif").DataTable({
        paging: false,
        searching: true,
        info: true,
        lengthChange: false,
        autoWidth: false,

        columns: [
            { data: "Id" },
            { data: "JenisBiaya" },
            { data: "Unit" },
            {
                data: "HInal",
                className: "text-end",
                render: $.fn.dataTable.render.number(",", ".", 0)
            },
            {
                data: "HPub",
                className: "text-end",
                render: $.fn.dataTable.render.number(",", ".", 0)
            },
            {
                data: "HCont",
                className: "text-end",
                render: $.fn.dataTable.render.number(",", ".", 0)
            },
            { data: "Ket" }
        ]
    });

    function loadTarif() {
        $.get("/tarif/api/list")
            .done(function (resp) {
                dtMasterTarif.clear().rows.add(resp.data || []).draw();
            })
            .fail(function () {
                window.myAlert("Gagal memuat master tarif", "error");
            });
    }

    $("#btnRefreshTarif").off().on("click", loadTarif);

    $("#txtFilterJenisBiaya").off().on("keyup change", function () {
        dtMasterTarif.column(1).search(this.value).draw();
    });

    loadTarif();
}
