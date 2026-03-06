function convertDate(txt){
    if (txt === "None") {
        return "-"
    }
    else {
        let year = txt.substring(0,4);
        let month = txt.substring(5,7);
        let date = txt.substring(8,10);
        return month + '/' + date + '/' + year;    
    }
}