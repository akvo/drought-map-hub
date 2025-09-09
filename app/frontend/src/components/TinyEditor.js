"use client";
import { Editor } from "@tinymce/tinymce-react";
import React, { useRef } from "react";

const TinyEditor = ({ value, setValue, height = 500 }) => {
  const editorRef = useRef(null);

  return (
    <Editor
      tinymceScriptSrc={"/assets/libs/tinymce/tinymce.min.js"}
      onInit={(_, editor) => (editorRef.current = editor)}
      value={value}
      init={{
        height,
        menubar: true,
        plugins: [
          "advlist",
          "autolink",
          "lists",
          "link",
          "image",
          "charmap",
          "preview",
          "anchor",
          "searchreplace",
          "visualblocks",
          "code",
          "fullscreen",
          "insertdatetime",
          "media",
          "table",
          "code",
          "help",
          "wordcount",
        ],
        toolbar:
          "undo redo | blocks | " +
          "bold italic forecolor | alignleft aligncenter " +
          "alignright alignjustify | bullist numlist outdent indent | " +
          "removeformat | help",
        content_style:
          "body { font-family:Helvetica,Arial,sans-serif; font-size:14px }",
      }}
      onEditorChange={setValue}
    />
  );
};

export default TinyEditor;
