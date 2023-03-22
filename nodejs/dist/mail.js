import fetch from "cross-fetch";
import { readFileSync, writeFile } from "fs";
const BASEURL = 'https://api.guerrillamail.com/ajax.php';
const createNewEmail2 = async (wx_id) => {
    const name = "flipturn" + Math.random();
    const response = await fetch(`https://maildrop.cc/page-data/inbox/page-data.json?mailbox=` + name);
    const response_json = await response.json();
    const credentials = JSON.parse(readFileSync("config.json", "utf8"));
    if (!credentials[wx_id]) {
        credentials[wx_id] = {};
    }
    credentials[wx_id].email = name + "@maildrop.cc";
    writeFile("config.json", JSON.stringify(credentials), function (err) {
        if (err) {
            console.log(err);
        }
    });
    return {
        email: credentials[wx_id].email,
        sid_token: name
    };
};
const getEmailList2 = async (email) => {
    let request = {
        operationName: 'GetInbox',
        query: "query GetInbox($mailbox: String!) {\n  ping(message: \"Test\")\n  inbox(mailbox: $mailbox) {\n    id\n    subject\n    date\n    headerfrom\n    __typename\n  }\n  altinbox(mailbox: $mailbox)\n}\n",
        variables: {
            mailbox: email,
        },
    };
    const response = await fetch(`https://api.maildrop.cc/graphql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', },
        body: JSON.stringify(request)
    });
    console.log("email=" + email);
    const response_json = await response.json();
    return {
        list: response_json.data.inbox,
    };
};
const getLatestEmail = async (sid_token) => {
    let emailList = await getEmailList2(sid_token);
    let emailListLength = emailList.list.length;
    if (emailListLength == 0) {
        for (let i = 0; i < 30; i++) {
            await new Promise(r => setTimeout(r, 1000));
            emailList = await getEmailList2(sid_token);
            emailListLength = emailList.list.length;
            if (emailListLength > 0) {
                break;
            }
        }
    }
    return emailList.list[0].id;
};
const getCodeId = async (name, id) => {
    console.log("name", name, "id", id);
    let request = {
        operationName: 'GetMessage',
        query: "query GetMessage($mailbox: String!, $id: String!) {message(mailbox: $mailbox, id: $id) {html\n}}",
        variables: {
            mailbox: name,
            id: id
        },
    };
    const response = await fetch(`https://api.maildrop.cc/graphql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', },
        body: JSON.stringify(request)
    });
    const response_json = await response.json();
    return response_json.data.message.html;
};
const getPoeOTPCode = async (sid_token) => {
    const emailDataId = await getLatestEmail(sid_token);
    let codeHtml = await getCodeId(sid_token, emailDataId);
    codeHtml = codeHtml.replace("\r\n", "");
    let patt = new RegExp(/>\d{6}</g);
    let arr = codeHtml.match(patt);
    let code = arr[0].substring(1, 7);
    console.log("emailData", code);
    console.log("OTP CODE: " + code);
    return code;
};
export { createNewEmail2, getLatestEmail, getPoeOTPCode };
