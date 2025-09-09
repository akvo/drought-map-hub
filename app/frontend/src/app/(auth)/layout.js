const AuthLayout = ({ children }) => {
  return (
    <div className="w-full min-h-screen bg-image-login bg-no-repeat bg-center bg-cover flex flex-row items-center justify-center">
      {children}
    </div>
  );
};

export default AuthLayout;
