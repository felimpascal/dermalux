

function drawTableBodyBudgetDetail(arrTHead,arrTBody,linkDetail,urlParam){
    let txtTBody = '';
    if (arrTBody.toString() != ""){
        let urlParameter = []
        for (let i = 0; i<arrTBody.length;i++){
            urlParameter[i] = `req=${btoa(urlParam[i])}`
            txtTBody += `<tr>`;
            for (let j = 0; j<arrTHead.length;j++){
                if (j >= 3 && j <= 5) {
                    if (parseInt(arrTBody[i][arrTHead[j]]).toLocaleString('en-US') == 0) {
                        txtTBody += `<td>-</td>`;
                    }   
                    else {
                        txtTBody += `<td>${parseInt(arrTBody[i][arrTHead[j]]).toLocaleString('en-US')}</td>`;
                    }     
                    
                }
                else {
                    txtTBody += `<td>${arrTBody[i][arrTHead[j]]}</td>`;
                }
            }
            txtTBody += `</tr>`;
        }
    }
    return txtTBody;
}

function drawTableHead(arrTHead){
    let txtThead = "";
    txtThead += "<tr>";
    for (let j = 0; j<arrTHead.length;j++){
        txtThead += `<th>${[arrTHead[j]]}</th>`;
    }
    txtThead += "</tr>";
    return txtThead;
}