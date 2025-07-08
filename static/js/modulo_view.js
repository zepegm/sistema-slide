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
                $("#letras_musicas").append(`<h4 class="text-primary">${response.titulo}</h4>`);

                for (let i = 0; i < response.letras.length; i++) {
                    $("#letras_musicas").append(`<p>${response.letras[i]['texto']}</p>`);
                }

                $("#show_musica").modal('show');
            }

        },
        error: function(err) {
            console.log(err);
        }
    }); 

}