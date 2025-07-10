function visualizar(id_item, tipo) {
    // primeiro enviar a requisição para o servidor
    $.ajax({
        type: "POST",
        url: "/historico",
        contentType: "application/json",
        data: JSON.stringify({destino:3, id_item: id_item, tipo: tipo}),
        dataType: "json",
        success: function(response) {
            console.log(response);

            if (response.destino == 'abrir_musica') {
                $("#letras_musicas").empty();
                $("#letras_musicas").append(`<h5 class="text-primary text-center fw-bold">${response.titulo}</h5>`);

                for (let i = 0; i < response.letras.length; i++) {
                    $("#letras_musicas").append(`<p>${response.letras[i]['texto']}</p>`);
                }

                $("#show_musica").modal('show');
            } else {
                $("#texto_biblia").empty();
                $("#showBibliaLabel").html(`<b>${response.titulo}, ${response.cap}</b>`);
                $("#texto_biblia").append(`<table class="table table-striped table-bordered"><thead id="thead_biblia" class="table-dark"></thead><tbody id="tbody_biblia"></tbody></table>`);

                let head = `<tr><th class="text-center" scope="col">Vers.</th>`;

                for (let i = 0; i < response.versoes.length; i++) {
                    head += `<th scope="col">${response.versoes[i].slice(-3).toUpperCase()}</th>`;
                }

                head += `</tr>`;

                $("#thead_biblia").append(head);

                let body = '';
                for (let i = 0; i < response.lista.length; i++) {
                    body += `<tr><td class="fw-bold display-5 text-center align-middle">${i + 1}</td>`;

                    for (let j = 0; j < response.versoes.length; j++) {
                        body += `<td class="align-middle auto_hifen">${response.lista[i][response.versoes[j]]}</td>`;
                    }

                    body += `</tr>`;
                }

                $("#tbody_biblia").append(body);

                $("#show_biblia").modal('show');
            }

        },
        error: function(err) {
            console.log(err);
        }
    }); 

}